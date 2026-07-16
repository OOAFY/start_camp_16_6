<template>
  <Teleport to="body">
  <div v-if="show" class="overlay" @click.self="close">
    <section class="modal" role="dialog" aria-modal="true" aria-labelledby="place-detail-title">
      <button class="close-button" type="button" aria-label="상세 정보 닫기" @click="close">×</button>

      <template v-if="place">
        <div class="detail-image">
          <img v-if="place.imageUrl || place.thumbnailUrl" :src="place.imageUrl || place.thumbnailUrl" :alt="place.title" />
          <div v-else class="image-placeholder">GUMI · GYEONGBUK LOCAL PLACE</div>
        </div>
        <div class="detail-body">
          <span class="place-chip">{{ place.region || place.contentType }}</span>
          <h2 id="place-detail-title">{{ place.title }}</h2>
          
          <dl class="detail-grid">
            <div><dt>유형</dt><dd>{{ place.contentType || '관광지' }}</dd></div>
            <div><dt>주소</dt><dd>{{ [place.address, place.detailAddress].filter(Boolean).join(' ') || '주소 정보 미등록' }}</dd></div>
            <div><dt>연락처</dt><dd>{{ place.telephone || '연락처 미등록' }}</dd></div>
            <div v-if="place.tags?.length"><dt>분위기</dt><dd class="detail-tags"><span v-for="tag in place.tags" :key="tag"># {{ tag }}</span></dd></div>
          </dl>

          <!-- 지도 영역 추가 -->
          <div v-if="hasCoordinates" class="detail-map-section">
            <h3 class="map-title">위치</h3>
            <div ref="mapElement" class="mini-map" aria-label="장소 위치 지도"></div>
          </div>
        </div>
      </template>

      <template v-else>
        <div class="detail-body">
          <p>장소 정보를 불러올 수 없습니다.</p>
        </div>
      </template>
    </section>
  </div>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const props = defineProps({
  show: { type: Boolean, default: false },
  place: { type: Object, default: null }
})

const emit = defineEmits(['update:show'])

const mapElement = ref(null)
let map = null
let marker = null

// 유효한 좌표가 있는지 확인하는 computed 속성
const hasCoordinates = computed(() => {
  return props.place && 
         Number.isFinite(props.place.latitude) && 
         Number.isFinite(props.place.longitude)
})

function close() {
  emit('update:show', false)
}

function handleKeydown(event) {
  if (event.key === 'Escape' && props.show) close()
}

function initMap() {
  if (!mapElement.value || !hasCoordinates.value) return

  const position = [props.place.latitude, props.place.longitude]

  // 지도가 이미 생성되어 있다면 뷰와 마커 위치만 업데이트
  if (map) {
    map.setView(position, 14)
    if (marker) {
      marker.setLatLng(position)
    }
  } else {
    // 줌 컨트롤을 제외하여 모달 안에서 깔끔하게 보이도록 설정
    map = L.map(mapElement.value, { zoomControl: false }).setView(position, 14)
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap'
    }).addTo(map)

    marker = L.marker(position).addTo(map)
  }

  // 모달 애니메이션 및 렌더링 이후 지도 크기를 재계산하여 회색 타일 오류 방지
  setTimeout(() => {
    map?.invalidateSize()
  }, 100)
}

function destroyMap() {
  if (map) {
    map.remove()
    map = null
    marker = null
  }
}

watch(() => props.show, (show) => {
  document.body.style.overflow = show ? 'hidden' : ''
  if (show) {
    window.addEventListener('keydown', handleKeydown)
    // 팝업이 열리고 좌표가 있다면 DOM 업데이트 후 지도 초기화
    if (hasCoordinates.value) {
      nextTick(() => initMap())
    }
  } else {
    window.removeEventListener('keydown', handleKeydown)
    destroyMap() // 팝업이 닫힐 때 지도 객체 정리
  }
})

onBeforeUnmount(() => {
  document.body.style.overflow = ''
  window.removeEventListener('keydown', handleKeydown)
  destroyMap()
})
</script>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(15, 28, 21, 0.55);
  backdrop-filter: blur(4px);
  z-index: 1000;
}
.modal {
  position: relative;
  width: min(520px, 100%);
  max-height: calc(100vh - 48px);
  overflow-y: auto;
  background: #fff;
  border-radius: 24px;
  box-shadow: 0 28px 80px rgba(0, 0, 0, 0.24);
}
.close-button {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 36px;
  height: 36px;
  
  /* Flexbox를 사용하여 '×'를 정중앙에 정렬 */
  display: flex;
  align-items: center;
  justify-content: center;
  padding-bottom: 2px; /* 폰트에 따라 세로 위치가 미세하게 쏠려 보일 경우 패딩으로 미세 조정 (필요에 따라 조절 또는 제거) */
  
  border: none;
  border-radius: 999px;
  background: rgba(255,255,255,.92);
  color: #24332a;
  font-size: 25px;
  line-height: 1; /* 글자 기본 높이로 인한 여백 제거 */
  cursor: pointer;
  z-index: 10;
}
.detail-image {
  width: 100%;
  height: 240px;
  overflow: hidden;
  border-radius: 24px 24px 0 0;
}
.detail-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.image-placeholder { display: grid; width: 100%; height: 100%; place-items: center; background: linear-gradient(135deg,#b9d4c3,#6c9f7f); color: rgba(255,255,255,.85); font-size: 11px; font-weight: 800; letter-spacing: 1px; }
.detail-body { padding: 26px 28px 30px; }
.place-chip { display: inline-block; padding: 6px 10px; border-radius: 999px; background: var(--green-100); color: var(--green-900); font-size: 11px; font-weight: 800; }
.detail-body h2 { margin: 3px 0 22px; color: var(--navy); font-size: 25px; }
.detail-grid {
  display: grid;
  gap: 0;
  margin: 0;
}
.detail-grid div { display: grid; grid-template-columns: 68px 1fr; gap: 12px; padding: 13px 0; border-top: 1px solid #edf0ed; }
.detail-grid dt { color: #879089; font-size: 13px; font-weight: 750; }
.detail-grid dd {
  margin: 0;
  color: #3e4a42;
  font-size: 14px;
  line-height: 1.55;
}
.detail-tags { display: flex; flex-wrap: wrap; gap: 6px; }
.detail-tags span { color: var(--green-800); font-size: 12px; font-weight: 700; }

/* 지도 영역 스타일 추가 */
.detail-map-section {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid #edf0ed;
}
.map-title {
  margin: 0 0 12px;
  color: #879089;
  font-size: 13px;
  font-weight: 750;
}
.mini-map {
  width: 100%;
  aspect-ratio: 1 / 1;
  border-radius: 12px;
  background: #e8efe9;
  border: 1px solid #edf0ed;
  z-index: 1; /* 모달 닫기 버튼을 덮지 않도록 제어 */
}

@media (max-width: 430px) {
  .overlay { padding: 12px; }
  .detail-image { height: 190px; }
  .detail-body { padding: 22px 20px 25px; }
}
</style>