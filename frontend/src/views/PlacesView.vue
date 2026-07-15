<template>
  <section class="places-page">
    <div class="page-hero">
      <div class="page-copy">
        <span class="hero-kicker">GUMI · GYEONGBUK LOCAL PLACES</span>
        <h1>구미·경북의 숨은 장소를<br />한눈에 둘러보세요</h1>
        <p class="hero-description">자연, 문화, 힐링, 음식까지<br />당신의 취향에 맞는 여행지를 발견해보세요.</p>

        <div class="hero-summary" aria-label="지역 장소 요약">
          <div>
            <strong>{{ places.length }}</strong>
            <span>추천 장소</span>
          </div>
          <span class="summary-divider" aria-hidden="true"></span>
          <div>
            <strong>{{ uniqueRegions.length }}</strong>
            <span>둘러볼 지역</span>
          </div>
        </div>
      </div>

      <div class="hero-side-card">
        <div class="recommend-heading">
          <div>
            <span class="recommend-kicker">{{ hasTravelPreference ? 'TASTE PICK' : 'RANDOM PICK' }}</span>
            <h2>이런 분위기 어때요?</h2>
          </div>
          <span class="recommend-label">{{ hasTravelPreference ? preferenceName : '새로운 발견' }}</span>
        </div>
        <div class="featured-tags" aria-label="분위기 태그">
          <button
            v-for="tag in featuredTags"
            :key="tag"
            type="button"
            :class="{ active: selectedTag === tag }"
            @click="selectedTag = tag"
          ># {{ tag }}</button>
        </div>
        <div v-if="recommendedPlaces.length" class="recommend-grid">
          <button
            v-for="place in recommendedPlaces"
            :key="place.contentId"
            class="recommend-card"
            type="button"
            @click="openPlace(place)"
          >
            <img v-if="place.thumbnailUrl || place.imageUrl" :src="place.thumbnailUrl || place.imageUrl" :alt="place.title" />
            <div v-else class="image-placeholder">LOCAL PLACE</div>
            <span class="recommend-overlay"><small>{{ place.region || place.contentType }}</small><strong>{{ place.title }}</strong></span>
          </button>
        </div>
        <div v-else class="recommend-empty">이 태그와 어울리는 장소를 찾고 있어요.</div>
      </div>
    </div>

    <div class="toolbar">
      <label class="search-box" for="place-search">
        <img :src="searchIcon" alt="" aria-hidden="true" />
        <input
          id="place-search"
          v-model="searchText"
          type="text"
          placeholder="장소명·주소·태그로 찾기"
        />
      </label>

      <div class="filter-group" role="tablist" aria-label="장소 유형 필터">
        <button
          v-for="option in typeOptions"
          :key="option.value"
          type="button"
          class="filter-chip"
          :class="{ active: selectedType === option.value }"
          @click="selectedType = option.value"
        >
          {{ option.label }}
        </button>
      </div>
    </div>

    <div v-if="filteredPlaces.length" class="place-grid">
      <article v-for="place in filteredPlaces" :key="place.contentId" class="place-card">
        <button type="button" class="place-button" @click="openPlace(place)">
          <div class="image-wrap">
            <img :src="place.thumbnailUrl || place.imageUrl" :alt="place.title" />
            <span class="category">{{ place.contentType }}</span>
            <span class="match">{{ place.tags.slice(0, 2).join(' · ') }}</span>
          </div>

          <div class="place-copy">
            <div class="place-meta">
              <span class="region">{{ place.region }}</span>
              <span class="type">{{ place.contentType }}</span>
            </div>
            <h3>{{ place.title }}</h3>
            <p>{{ place.address }}</p>
            <div class="tag-list">
              <span v-for="tag in place.tags" :key="tag">{{ tag }}</span>
            </div>
          </div>
        </button>
      </article>
    </div>

    <div v-else class="empty-state">
      <h3>조건에 맞는 장소가 없어요</h3>
      <p>검색어 또는 필터를 바꿔서 다시 찾아보세요.</p>
    </div>

    <PlaceDetailModal
      :show="showPlaceModal"
      :place="selectedPlace"
      @update:show="showPlaceModal = $event"
    />
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { fetchPlaces, fetchPlaceDetail } from '../api'
import PlaceDetailModal from '../components/PlaceDetailModal.vue'
import searchIcon from '../assets/search.png'

const route = useRoute()
const places = ref([])
const selectedPlace = ref(null)
const showPlaceModal = ref(false)
const searchText = ref('')
const selectedType = ref('all')
const selectedTag = ref('')
const RESULT_KEY = 'localhub-travel-type'
const preferenceCode = ref('')
const randomOrder = ref([])

const preferenceProfiles = {
  HEALING: { name: '고요한 쉼표 수집가', tags: ['힐링', '자연', '산책', '휴식', '조용함', '공원'] },
  EXPLORER: { name: '에너지 만렙 탐험가', tags: ['레포츠', '체험', '액티비티', '등산', '모험', '걷기'] },
  CULTURE: { name: '이야기를 좇는 시간여행자', tags: ['역사', '문화', '전시', '박물관', '전통', '예술'] },
  FOODIE: { name: '한입에 담는 로컬 미식가', tags: ['음식', '맛집', '시장', '카페', '로컬', '먹거리'] }
}

const typeOptions = [
  { value: 'all', label: '전체' },
  { value: '관광지', label: '관광지' },
  { value: '문화시설', label: '문화시설' },
  { value: '음식점', label: '음식점' },
  { value: '레포츠', label: '레포츠' }
]

function normalizePlace(raw) {
  const item = raw || {}

  return {
    contentId: item.contentId || item.content_id || '',
    contentType: item.contentType || item.content_type || '',
    title: item.title || '',
    address: item.address || '',
    detailAddress: item.detailAddress || item.detail_address || '',
    telephone: item.telephone || '',
    imageUrl: item.imageUrl || item.image_url || '',
    thumbnailUrl: item.thumbnailUrl || item.thumbnail_url || '',
    region: item.region || '',
    tags: Array.isArray(item.tags) ? item.tags : [],
    latitude: item.latitude ?? item.mapY ?? item.map_y ?? null,
    longitude: item.longitude ?? item.mapX ?? item.map_x ?? null
  }
}

const uniqueRegions = computed(() => [...new Set(places.value.map((place) => place.region))])
const hasTravelPreference = computed(() => Boolean(preferenceProfiles[preferenceCode.value]))
const preferenceName = computed(() => preferenceProfiles[preferenceCode.value]?.name || '')
const allTags = computed(() => [...new Set(places.value.flatMap((place) => place.tags || []).filter(Boolean))])
const featuredTags = computed(() => {
  const orderedTags = randomOrder.value.filter((tag) => allTags.value.includes(tag))
  if (!hasTravelPreference.value) return orderedTags.slice(0, 5)

  const preferred = preferenceProfiles[preferenceCode.value].tags
  const matched = allTags.value.filter((tag) => preferred.some((keyword) => tag.includes(keyword) || keyword.includes(tag)))
  return [...new Set([...matched, ...orderedTags])].slice(0, 5)
})

const recommendedPlaces = computed(() => {
  const exactMatches = selectedTag.value
    ? places.value.filter((place) => place.tags.includes(selectedTag.value))
    : places.value
  const preferredTags = preferenceProfiles[preferenceCode.value]?.tags || []
  const sortByPreference = (items) => [...items]
    .sort((a, b) => {
      const score = (place) => place.tags.reduce((sum, tag) => sum + (preferredTags.some((keyword) => tag.includes(keyword) || keyword.includes(tag)) ? 1 : 0), 0)
      return score(b) - score(a) || randomOrder.value.indexOf(a.contentId) - randomOrder.value.indexOf(b.contentId)
    })

  const exactRecommendations = sortByPreference(exactMatches)
  if (exactRecommendations.length >= 2) return exactRecommendations.slice(0, 2)

  // 정확히 일치하는 장소가 하나뿐이면 중복 카드 대신 취향이 가까운 장소로 빈자리를 채웁니다.
  const exactIds = new Set(exactRecommendations.map((place) => place.contentId))
  const relatedRecommendations = sortByPreference(places.value.filter((place) => !exactIds.has(place.contentId)))
  return [...exactRecommendations, ...relatedRecommendations].slice(0, 2)
})

const filteredPlaces = computed(() => {
  const term = searchText.value.trim().toLowerCase()

  return places.value.filter((place) => {
    const matchesType = selectedType.value === 'all' || place.contentType === selectedType.value
    const haystack = [place.title, place.address, place.region, place.contentType, ...(place.tags || [])]
      .join(' ')
      .toLowerCase()

    return matchesType && (!term || haystack.includes(term))
  })
})

async function loadPlaces() {
  try {
    const res = await fetchPlaces({
      size: 100,
      type: selectedType.value === 'all' ? undefined : selectedType.value,
      keyword: searchText.value || undefined
    })

    const payload = res?.items || res || []
    places.value = Array.isArray(payload) ? payload.map(normalizePlace) : []
    randomOrder.value = [...places.value.map((place) => place.contentId), ...allTags.value].sort(() => Math.random() - 0.5)
    selectedTag.value = featuredTags.value[0] || ''
  } catch (error) {
    places.value = []
  }
}

onMounted(() => {
  preferenceCode.value = sessionStorage.getItem(RESULT_KEY) || ''
  loadPlaces()
})

watch([selectedType, searchText], () => {
  loadPlaces()
})

async function openPlace(place) {
  try {
    const detail = await fetchPlaceDetail(place.contentId)
    selectedPlace.value = normalizePlace(detail || place)
  } catch (error) {
    selectedPlace.value = normalizePlace(place)
  }

  showPlaceModal.value = true
}

watch(
  () => route.query.selected,
  (selectedId) => {
    if (!selectedId) return

    const place = places.value.find((item) => item.contentId === selectedId)
    if (place) {
      openPlace(place)
    }
  },
  { immediate: true }
)
</script>

<style scoped>
.places-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.page-hero {
  display: grid;
  grid-template-columns: 1.05fr 0.95fr;
  gap: 18px;
  align-items: stretch;
}

.page-copy,
.hero-side-card {
  padding: 28px;
  border: 1px solid var(--line);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.88);
  box-shadow: var(--shadow);
}

.hero-kicker,
.recommend-kicker {
  display: inline-block;
  margin-bottom: 12px;
  color: var(--green-700);
  font-size: 11px;
  font-weight: 850;
  letter-spacing: 1.8px;
}

.page-copy h1 {
  margin: 0;
  color: var(--navy);
  font-size: clamp(28px, 3vw, 40px);
  line-height: 1.2;
  letter-spacing: -1.4px;
}

.page-copy { display: flex; flex-direction: column; }
.page-copy p {
  margin: 14px 0 0;
  color: #5d665e;
  font-size: 15px;
  line-height: 1.7;
}

.hero-summary { display: flex; align-items: center; gap: 22px; margin-top: auto; padding-top: 22px; }
.hero-summary div { display: grid; grid-template-columns: auto 1fr; gap: 3px 8px; align-items: baseline; }
.hero-summary strong {
  grid-row: 1 / 3;
  color: var(--green-900);
  font-size: 28px;
  line-height: 1;
}
.hero-summary span:not(.summary-divider) {
  color: #627065;
  font-size: 12px;
  font-weight: 700;
}
.summary-divider { width: 1px; height: 30px; background: #dfe6e1; }

.recommend-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.recommend-heading h2 {
  margin: 4px 0 0;
  font-size: 20px;
  color: var(--navy);
}
.recommend-label { padding: 7px 11px; border-radius: 999px; background: var(--green-100); color: var(--green-900); font-size: 11px; font-weight: 800; white-space: nowrap; }
.featured-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 14px;
}
.featured-tags button {
  padding: 6px 10px;
  border: 1px solid transparent;
  border-radius: 999px;
  background: var(--green-100);
  color: var(--green-900);
  font-size: 11px;
  font-weight: 700;
}
.featured-tags button.active { border-color: var(--green-700); background: var(--green-800); color: #fff; }
.recommend-grid { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 10px; margin-top: 14px; }
.recommend-card { position: relative; height: 122px; padding: 0; overflow: hidden; border: 0; border-radius: 16px; background: #dfe9e2; color: #fff; text-align: left; }
.recommend-card img { width: 100%; height: 100%; object-fit: cover; transition: transform .25s ease; }
.recommend-card:hover img { transform: scale(1.04); }
.recommend-overlay { position: absolute; inset: auto 0 0; display: flex; flex-direction: column; gap: 2px; padding: 26px 12px 10px; background: linear-gradient(transparent,rgba(14,31,23,.88)); }
.recommend-overlay small { font-size: 10px; opacity: .85; }
.recommend-overlay strong { overflow: hidden; font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
.recommend-empty { display: grid; min-height: 122px; margin-top: 14px; place-items: center; border-radius: 16px; background: #f4f7f4; color: #778079; font-size: 13px; }
.image-placeholder { display: grid; width: 100%; height: 100%; place-items: center; background: linear-gradient(135deg,#b9d4c3,#6c9f7f); font-size: 10px; font-weight: 800; letter-spacing: 1px; }

.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 0;
}

.search-box {
  flex: 1 1 280px;
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 48px;
  padding: 0 14px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: #fff;
  box-shadow: 0 6px 20px rgba(17, 28, 44, 0.04);
}

.search-box input {
  width: 100%;
  border: none;
  outline: none;
  background: transparent;
  color: var(--navy);
}
.search-box img { width: 21px; height: 21px; object-fit: contain; filter: invert(35%) sepia(18%) saturate(1190%) hue-rotate(97deg) brightness(88%); }

.filter-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.filter-chip {
  padding: 8px 12px;
  border-radius: 999px;
  background: #f5f5eb;
  color: #5d665e;
  font-size: 13px;
  font-weight: 700;
}

.filter-chip.active {
  color: #fff;
  background: var(--green-800);
}

.place-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.place-card {
  border: 1px solid var(--line);
  border-radius: 20px;
  background: #fff;
  box-shadow: 0 10px 26px rgba(35, 52, 43, 0.06);
  overflow: hidden;
  transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease;
}
.place-card:hover { transform: translateY(-2px); border-color: #a8cbb4; box-shadow: 0 12px 28px rgba(35,52,43,.1); }

.place-button {
  width: 100%;
  padding: 0;
  text-align: left;
  background: none;
  border: none;
}

.image-wrap {
  position: relative;
  aspect-ratio: 1.35;
  overflow: hidden;
  background: #e9f0e4;
}

.image-wrap img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.place-copy {
  padding: 16px;
}

.place-copy h3 {
  margin: 0 0 8px;
  color: var(--navy);
  font-size: 20px;
}

.place-copy p {
  margin: 0 0 10px;
  color: #5d665e;
  line-height: 1.6;
}

.place-meta {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
  color: #6b736f;
  font-size: 12px;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag-list span {
  padding: 5px 8px;
  border-radius: 999px;
  background: var(--green-100);
  color: var(--green-900);
  font-size: 11px;
}

@media (max-width: 800px) {
  .page-hero, .place-grid { grid-template-columns: 1fr; }
  .page-copy, .hero-side-card { padding: 20px; }
  .hero-summary { margin-top: 24px; }
}
@media (max-width: 480px) {
  .recommend-grid { grid-template-columns: 1fr; }
  .recommend-card { height: 150px; }
  .hero-summary { gap: 14px; }
}
</style>
