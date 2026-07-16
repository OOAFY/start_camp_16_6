<template>
  <section class="map-page">
    <header class="map-heading">
      <div>
        <span class="map-kicker">GUMI · GYEONGBUK MAP</span>
        <h1>지도에서 지역 명소를 찾아보세요</h1>
        <p>마커를 선택하면 장소 정보를 확인하고 상세 화면을 열 수 있습니다.</p>
      </div>
      <div class="map-summary" aria-live="polite">
        <strong>{{ visiblePlaces.length }}</strong>
        <span>개 장소 표시 중</span>
      </div>
    </header>

    <div class="map-toolbar">
      <label class="search-field" for="map-search">
        <img :src="searchIcon" alt="" aria-hidden="true" />
        <input
          id="map-search"
          v-model="searchText"
          type="search"
          placeholder="장소명 또는 주소 검색"
        />
      </label>

      <label class="region-field" for="map-region">
        <span>지역</span>
        <select id="map-region" v-model="selectedRegion">
          <option value="all">전체 지역</option>
          <option v-for="region in regions" :key="region" :value="region">{{ region }}</option>
        </select>
      </label>
    </div>

    <div class="map-shell">
      <div v-if="loading" class="map-status">지도에 표시할 장소를 불러오고 있습니다.</div>
      <div v-else-if="errorMessage" class="map-status map-status--error">
        <strong>장소를 불러오지 못했습니다.</strong>
        <span>{{ errorMessage }}</span>
        <button type="button" @click="loadPlaces">다시 시도</button>
      </div>
      <div ref="mapElement" class="map-canvas" :class="{ 'is-hidden': loading || errorMessage }" aria-label="구미·경북 지역 장소 지도"></div>
      <div v-if="tileErrorMessage && !loading && !errorMessage" class="tile-warning" role="status">
        {{ tileErrorMessage }}
      </div>
    </div>

    <p class="map-attribution-note">지도 마커에는 좌표가 등록된 장소만 표시됩니다.</p>

    <PlaceDetailModal
      :show="showPlaceModal"
      :place="selectedPlace"
      @update:show="showPlaceModal = $event"
    />
  </section>
</template>

<script setup>
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import 'leaflet.markercluster'
import 'leaflet.markercluster/dist/MarkerCluster.css'
import 'leaflet.markercluster/dist/MarkerCluster.Default.css'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { fetchPlaceDetail, fetchPlaces } from '../api'
import searchIcon from '../assets/search.png'
import PlaceDetailModal from '../components/PlaceDetailModal.vue'

const route = useRoute()

const DEFAULT_CENTER = [36.1195, 128.3446]
const DEFAULT_ZOOM = 9
const KOREA_BOUNDS = {
  south: 33,
  north: 39,
  west: 124,
  east: 132
}
const PLACE_MARKER_ICON = L.divIcon({
  className: 'localhub-place-marker',
  html: '<span aria-hidden="true"></span>',
  iconSize: [30, 38],
  iconAnchor: [15, 38],
  popupAnchor: [0, -34]
})

const mapElement = ref(null)
const places = ref([])
const loading = ref(true)
const errorMessage = ref('')
const tileErrorMessage = ref('')
const searchText = ref('')
const selectedRegion = ref('all')
const selectedPlace = ref(null)
const showPlaceModal = ref(false)

let map = null
let markerLayer = null
let activeTileLayer = null
let tileErrorCount = 0
let usingFallbackTiles = false

const regions = computed(() => [...new Set(places.value.map((place) => place.region).filter(Boolean))].sort())
const visiblePlaces = computed(() => {
  const keyword = searchText.value.trim().toLowerCase()

  return places.value.filter((place) => {
    const matchesRegion = selectedRegion.value === 'all' || place.region === selectedRegion.value
    const haystack = [place.title, place.address, place.region, place.contentType].filter(Boolean).join(' ').toLowerCase()
    return matchesRegion && (!keyword || haystack.includes(keyword))
  })
})

function normalizePlace(raw) {
  const latitude = Number(raw?.latitude ?? raw?.mapY ?? raw?.map_y)
  const longitude = Number(raw?.longitude ?? raw?.mapX ?? raw?.map_x)

  return {
    ...raw,
    contentId: String(raw?.contentId ?? raw?.content_id ?? ''),
    contentType: raw?.contentType ?? raw?.content_type ?? '',
    detailAddress: raw?.detailAddress ?? raw?.detail_address ?? '',
    imageUrl: raw?.imageUrl ?? raw?.image_url ?? '',
    thumbnailUrl: raw?.thumbnailUrl ?? raw?.thumbnail_url ?? '',
    tags: Array.isArray(raw?.tags) ? raw.tags : [],
    latitude,
    longitude
  }
}

function hasValidKoreaCoordinates(place) {
  return Number.isFinite(place.latitude)
    && Number.isFinite(place.longitude)
    && place.latitude >= KOREA_BOUNDS.south
    && place.latitude <= KOREA_BOUNDS.north
    && place.longitude >= KOREA_BOUNDS.west
    && place.longitude <= KOREA_BOUNDS.east
}

function createPopup(place) {
  const wrapper = document.createElement('div')
  wrapper.className = 'localhub-map-popup'

  const meta = document.createElement('span')
  meta.textContent = [place.region, place.contentType].filter(Boolean).join(' · ')

  const title = document.createElement('strong')
  title.textContent = place.title

  const address = document.createElement('p')
  address.textContent = place.address || '주소 정보 미등록'

  const button = document.createElement('button')
  button.type = 'button'
  button.textContent = '상세 보기'
  button.addEventListener('click', () => openPlace(place))

  wrapper.append(meta, title, address, button)
  return wrapper
}

function initializeMap() {
  if (map || !mapElement.value) return

  map = L.map(mapElement.value, { zoomControl: true }).setView(DEFAULT_CENTER, DEFAULT_ZOOM)

  usePrimaryTiles()

  // 많은 마커를 한 프레임에 그리지 않고 묶어서 표시해 화면 멈춤을 줄입니다.
  markerLayer = L.markerClusterGroup({
    chunkedLoading: true,
    chunkInterval: 100,
    chunkDelay: 30,
    removeOutsideVisibleBounds: true,
    showCoverageOnHover: false,
    zoomToBoundsOnClick: false,
    spiderfyOnMaxZoom: true,
    maxClusterRadius: 54
  }).addTo(map)

  markerLayer.on('clusterclick', ({ layer }) => {
    const childMarkers = layer.getAllChildMarkers()
    const firstPosition = childMarkers[0]?.getLatLng()
    const isSamePosition = firstPosition && childMarkers.every((marker) => {
      const position = marker.getLatLng()
      return position.lat === firstPosition.lat && position.lng === firstPosition.lng
    })

    // 여러 장소가 같은 좌표를 공유하면 확대를 반복하지 않고 즉시 핀을 펼칩니다.
    if (isSamePosition) {
      layer.spiderfy()
      return
    }

    // 서로 가까운 장소들의 묶음은 기존처럼 해당 영역까지 확대합니다.
    layer.zoomToBounds({ padding: [36, 36] })
  })
}

function bindTileEvents(tileLayer) {
  tileLayer.on('tileload', () => {
    tileErrorMessage.value = ''
  })
  tileLayer.on('tileerror', () => {
    tileErrorCount += 1

    if (!usingFallbackTiles && tileErrorCount >= 3) {
      useFallbackTiles()
      return
    }

    if (usingFallbackTiles && tileErrorCount >= 3) {
      tileErrorMessage.value = '배경 지도 제공자에 연결하지 못했습니다. 네트워크 상태를 확인해 주세요.'
    }
  })
  return tileLayer
}

function replaceTileLayer(nextLayer) {
  if (activeTileLayer && map?.hasLayer(activeTileLayer)) map.removeLayer(activeTileLayer)
  activeTileLayer = bindTileEvents(nextLayer)
  activeTileLayer.addTo(map)
}

function createBackgroundTileLayer(urlTemplate, options = {}) {
  const BackgroundTileLayer = L.GridLayer.extend({
    createTile(coords, done) {
      const tile = document.createElement('div')
      tile.className = 'localhub-map-tile'
      const subdomains = options.subdomains || ''
      const url = L.Util.template(urlTemplate, {
        ...coords,
        s: subdomains[Math.abs(coords.x + coords.y) % subdomains.length] || ''
      })
      const image = new Image()

      image.onload = () => {
        tile.style.backgroundImage = `url("${url}")`
        done(null, tile)
      }
      image.onerror = () => done(new Error(`Map tile failed: ${url}`), tile)
      image.src = url
      return tile
    }
  })

  return new BackgroundTileLayer({
    tileSize: 256,
    maxZoom: options.maxZoom,
    attribution: options.attribution
  })
}

function usePrimaryTiles() {
  usingFallbackTiles = false
  tileErrorCount = 0
  tileErrorMessage.value = ''
  replaceTileLayer(createBackgroundTileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    subdomains: 'abc',
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
  }))
}

function useFallbackTiles() {
  usingFallbackTiles = true
  tileErrorCount = 0
  tileErrorMessage.value = '기본 지도를 불러오지 못해 보조 지도로 전환했습니다.'
  replaceTileLayer(createBackgroundTileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}', {
    maxZoom: 16,
    attribution: 'Tiles &copy; Esri'
  }))
}

function renderMarkers() {
  if (!map || !markerLayer) return

  markerLayer.clearLayers()
  const bounds = []

  visiblePlaces.value.forEach((place) => {
    const position = [place.latitude, place.longitude]
    L.marker(position, {
      icon: PLACE_MARKER_ICON,
      title: place.title,
      alt: `${place.title} 위치`
    }).bindPopup(createPopup(place), { minWidth: 210 }).addTo(markerLayer)
    bounds.push(position)
  })

  if (bounds.length) {
    map.fitBounds(bounds, { padding: [36, 36], maxZoom: 14 })
  } else {
    map.setView(DEFAULT_CENTER, DEFAULT_ZOOM)
  }
}

async function focusRequestedPlace(contentId = route.query.selected) {
  const requestedId = String(contentId || '')
  if (!requestedId || !map) return

  const place = places.value.find((item) => item.contentId === requestedId)
  if (!place) return

  selectedRegion.value = 'all'
  searchText.value = ''
  await nextTick()
  renderMarkers()
  map.setView([place.latitude, place.longitude], 15)
  await openPlace(place)
}

async function loadPlaces() {
  loading.value = true
  errorMessage.value = ''

  try {
    // 지도에서는 페이지 구분 없이 좌표가 있는 장소를 한 번에 받아 마커로 표시합니다.
    const response = await fetchPlaces({ page: 1, size: 2000 })
    const items = response?.items || response || []
    places.value = (Array.isArray(items) ? items : [])
      .map(normalizePlace)
      .filter(hasValidKoreaCoordinates)

    await nextTick()
    initializeMap()
    map?.invalidateSize()
    renderMarkers()
    await focusRequestedPlace()
  } catch (error) {
    errorMessage.value = error?.message || '잠시 후 다시 시도해 주세요.'
  } finally {
    loading.value = false
    await nextTick()
    map?.invalidateSize()
  }
}

async function openPlace(place) {
  try {
    const detail = await fetchPlaceDetail(place.contentId)
    selectedPlace.value = normalizePlace(detail || place)
  } catch (error) {
    selectedPlace.value = place
  }
  showPlaceModal.value = true
}

watch(visiblePlaces, () => renderMarkers(), { flush: 'post' })
watch(() => route.query.selected, (contentId) => focusRequestedPlace(contentId))

onMounted(loadPlaces)

onBeforeUnmount(() => {
  map?.remove()
  map = null
  markerLayer = null
  activeTileLayer = null
})
</script>

<style scoped>
.map-page { display: flex; flex-direction: column; gap: 20px; }
.map-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  padding: 28px;
  border: 1px solid var(--line);
  border-radius: 24px;
  background: rgba(255, 255, 255, .88);
  box-shadow: var(--shadow);
}
.map-kicker { color: var(--green-700); font-size: 11px; font-weight: 850; letter-spacing: 1.8px; }
.map-heading h1 { margin: 8px 0; color: var(--navy); font-size: clamp(27px, 3vw, 39px); letter-spacing: -1.4px; }
.map-heading p { margin: 0; color: var(--muted); line-height: 1.65; }
.map-summary { display: flex; align-items: baseline; gap: 7px; min-width: max-content; color: var(--green-900); }
.map-summary strong { font-size: 34px; }
.map-summary span { font-size: 13px; font-weight: 750; }
.map-toolbar { display: flex; gap: 12px; }
.search-field, .region-field {
  display: flex;
  align-items: center;
  min-height: 50px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: #fff;
}
.search-field { flex: 1; gap: 10px; padding: 0 16px; }
.search-field img { width: 21px; height: 21px; object-fit: contain; filter: invert(35%) sepia(18%) saturate(1190%) hue-rotate(97deg) brightness(88%); }
.search-field input { width: 100%; border: 0; outline: 0; background: transparent; color: var(--navy); }
.region-field { gap: 10px; padding: 0 12px 0 16px; }
.region-field span { color: var(--muted); font-size: 12px; font-weight: 750; }
.region-field select { min-width: 120px; border: 0; outline: 0; background: #fff; color: var(--navy); }
.map-shell { position: relative; min-height: 610px; overflow: hidden; border: 1px solid var(--line); border-radius: 24px; background: #e8efe9; box-shadow: var(--shadow); }
.map-canvas { width: 100%; height: 610px; }
.map-canvas.is-hidden { visibility: hidden; }
.map-status { position: absolute; inset: 0; z-index: 2; display: grid; place-content: center; gap: 10px; color: var(--muted); text-align: center; }
.map-status--error strong { color: var(--navy); }
.map-status--error button { justify-self: center; padding: 9px 14px; border-radius: 9px; background: var(--green-800); color: #fff; font-weight: 750; }
.map-attribution-note { margin: -8px 4px 0; color: var(--muted); font-size: 12px; }
.tile-warning {
  position: absolute;
  z-index: 500;
  right: 14px;
  bottom: 28px;
  max-width: min(420px, calc(100% - 28px));
  padding: 10px 13px;
  border: 1px solid #efc8bb;
  border-radius: 10px;
  background: rgba(255, 247, 243, .96);
  color: #914a31;
  font-size: 12px;
  line-height: 1.5;
  box-shadow: 0 8px 24px rgba(69, 38, 27, .12);
}

:deep(.localhub-map-tile) {
  width: 256px;
  height: 256px;
  background-position: center;
  background-repeat: no-repeat;
  background-size: 256px 256px;
}

:deep(.localhub-place-marker) {
  border: 0;
  background: transparent;
}

:deep(.localhub-place-marker span) {
  position: relative;
  display: block;
  width: 30px;
  height: 30px;
  border: 3px solid #fff;
  border-radius: 50% 50% 50% 0;
  background: var(--green-800);
  box-shadow: 0 5px 14px rgba(16, 67, 45, .35);
  transform: rotate(-45deg);
}

:deep(.localhub-place-marker span::after) {
  position: absolute;
  top: 8px;
  left: 8px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #fff;
  content: '';
}

:deep(.marker-cluster-small),
:deep(.marker-cluster-medium),
:deep(.marker-cluster-large) { background: rgba(22, 129, 82, .24); }
:deep(.marker-cluster-small div),
:deep(.marker-cluster-medium div),
:deep(.marker-cluster-large div) { background: var(--green-800); color: #fff; font-weight: 800; }

:deep(.leaflet-popup-content-wrapper) { border-radius: 14px; box-shadow: 0 12px 34px rgba(16, 32, 22, .18); }
:deep(.localhub-map-popup) { display: flex; flex-direction: column; gap: 7px; }
:deep(.localhub-map-popup span) { color: var(--green-700); font-size: 11px; font-weight: 750; }
:deep(.localhub-map-popup strong) { color: var(--navy); font-size: 16px; }
:deep(.localhub-map-popup p) { margin: 0; color: var(--muted); font-size: 12px; line-height: 1.5; }
:deep(.localhub-map-popup button) { align-self: flex-start; margin-top: 3px; padding: 7px 10px; border-radius: 8px; background: var(--green-800); color: #fff; font-size: 12px; font-weight: 750; }

@media (max-width: 720px) {
  .map-heading { align-items: flex-start; flex-direction: column; padding: 22px; }
  .map-toolbar { flex-direction: column; }
  .region-field select { flex: 1; }
  .map-shell, .map-canvas { min-height: 520px; height: 520px; }
}
</style>
