<script setup>
import { computed, onMounted, ref } from 'vue'

import CommunityPanel from '../components/CommunityPanel.vue'
import FestivalPanel from '../components/FestivalPanel.vue'
import PlaceCard from '../components/PlaceCard.vue'
import SiteFooter from '../components/SiteFooter.vue'
import TravelTestModal from '../components/TravelTestModal.vue'
import TypeCard from '../components/TypeCard.vue'
import { festivals, heroImages, travelTypes } from '../data/homeMock'
import { fetchPlaces, fetchPosts } from '../api'

const RESULT_KEY = 'localhub-travel-type'
const ONBOARDING_KEY = 'localhub-onboarding-seen'
const showTravelTest = ref(false)
const hasResult = ref(false)
const resultCode = ref('HEALING')
const places = ref([])
const posts = ref([])

const resultType = computed(() => travelTypes.find((type) => type.code === resultCode.value) || travelTypes[0])

function normalizePlace(place) {
  const item = place || {}

  return {
    contentId: item.contentId || item.content_id || item.id || '',
    imageUrl: item.imageUrl || item.image_url || item.thumbnailUrl || item.thumbnail_url || '',
    category: item.contentType || item.content_type || '관광지',
    matchedKeywords: Array.isArray(item.tags) ? item.tags : [],
    shortTitle: item.title || '',
    description: item.address || item.detailAddress || item.detail_address || '',
    title: item.title || '',
    region: item.region || '',
    address: item.address || ''
  }
}

function normalizePost(post) {
  const item = post || {}

  return {
    id: item.id,
    category: item.category || '여행',
    title: item.title || '',
    views: item.viewCount ?? item.view_count ?? 0,
    time: item.createdAt ? item.createdAt.slice(0, 10) : (item.created_at ? item.created_at.slice(0, 10) : ''),
    tone: item.category === '맛집' ? 'blue' : item.category === '축제' ? 'purple' : 'green',
    content: item.content || ''
  }
}

onMounted(async () => {
  const savedType = sessionStorage.getItem(RESULT_KEY)
  const onboardingSeen = sessionStorage.getItem(ONBOARDING_KEY) === 'true'
  if (savedType) {
    resultCode.value = savedType
    hasResult.value = true
  }
  showTravelTest.value = !onboardingSeen

  try {
    const [placeRes, postRes] = await Promise.all([
      fetchPlaces({ size: 6 }),
      fetchPosts({ size: 4 })
    ])

    const placeItems = placeRes?.items || placeRes || []
    const postItems = postRes?.items || postRes || []

    places.value = Array.isArray(placeItems) ? placeItems.map(normalizePlace) : []
    posts.value = Array.isArray(postItems) ? postItems.map(normalizePost) : []
  } catch (error) {
    places.value = []
    posts.value = []
  }
})

function openTravelTest() {
  showTravelTest.value = true
}

function skipTravelTest() {
  sessionStorage.setItem(ONBOARDING_KEY, 'true')
  showTravelTest.value = false
}

function completeTravelTest(_answers) {
  resultCode.value = 'HEALING'
  hasResult.value = true
  showTravelTest.value = false
  sessionStorage.setItem(ONBOARDING_KEY, 'true')
  sessionStorage.setItem(RESULT_KEY, resultCode.value)
}

function previewType(code) {
  resultCode.value = code
  hasResult.value = true
}
</script>

<template>
  <div class="page-shell">
    <main>
      <section class="hero container">
        <div class="hero-copy">
          <span class="hero-kicker">GUMI · GYEONGBUK LOCAL TRAVEL</span>
          <h1>내 취향으로 발견하는<br /><em>구미·경북</em> 여행</h1>
          <p>몇 가지 질문만으로 당신에게 딱 맞는<br />구미·경북 여행지를 추천해드려요.</p>
          <div class="hero-actions">
            <button class="btn btn--primary" type="button" @click="openTravelTest">
              {{ hasResult ? '취향 테스트 다시 하기' : '여행 취향 테스트 시작' }} <span>›</span>
            </button>
            <router-link class="btn btn--outline" to="/places">지역 먼저 둘러보기 <span>›</span></router-link>
          </div>
        </div>

        <div class="hero-gallery" aria-label="구미·경북 추천 여행지 미리보기">
          <div class="route-line" aria-hidden="true"></div>
          <div v-for="(image, index) in heroImages" :key="image.src" class="hero-image" :class="`image-${index + 1}`">
            <img :src="image.src" :alt="image.alt" />
          </div>
          <div class="result-badge">
            <span class="result-icon" aria-hidden="true">{{ resultType.icon }}</span>
            <span><small>당신의 여행 성향은</small><strong>{{ resultType.name }}</strong></span>
            <b aria-hidden="true">✦</b>
          </div>
        </div>
      </section>

      <section class="type-grid container" aria-label="여행 취향 유형">
        <TypeCard v-for="type in travelTypes" :key="type.code" :type="type" @select="previewType" />
      </section>

      <section class="dashboard container">
        <div class="recommendations">
          <header class="section-header">
            <div>
              <h2 v-if="hasResult"><em>'{{ resultType.name }}'</em>인 당신을 위한 지역 추천</h2>
              <h2 v-else>당신을 위한 지역 추천</h2>
              <p v-if="hasResult">자연 · 휴식 · 조용함 키워드를 바탕으로 골랐어요</p>
              <p v-else>취향 테스트를 완료하면 더 잘 맞는 여행지를 보여드려요</p>
            </div>
            <router-link to="/places">더보기 <span>›</span></router-link>
          </header>
          <div class="place-grid">
            <PlaceCard v-for="place in places" :key="place.contentId" :place="place" />
          </div>
        </div>

        <FestivalPanel :festivals="festivals" />
        <CommunityPanel :posts="posts" />
      </section>
    </main>

    <SiteFooter />
    <TravelTestModal v-if="showTravelTest" @complete="completeTravelTest" @skip="skipTravelTest" />
  </div>
</template>

<style scoped>
.page-shell { min-height: 100vh; overflow: hidden; }
.hero { min-height: 345px; display: grid; grid-template-columns: .86fr 1.14fr; align-items: center; gap: 52px; padding-top: 30px; padding-bottom: 26px; }
.hero-kicker { display: inline-block; margin-bottom: 13px; color: var(--green-700); font-size: 11px; font-weight: 850; letter-spacing: 1.8px; }
.hero-copy h1 { margin: 0; color: var(--navy); font-size: clamp(43px, 4.15vw, 64px); line-height: 1.18; letter-spacing: -2.8px; }
.hero-copy h1 em { color: var(--green-900); font-style: normal; }
.hero-copy p { margin: 22px 0; color: #56605b; font-size: 16px; line-height: 1.65; }
.hero-actions { display: flex; gap: 16px; }
.hero-actions span { font-size: 24px; font-weight: 300; line-height: 1; }
.hero-gallery { position: relative; height: 300px; display: grid; grid-template-columns: 1.05fr 1.1fr 1fr; align-items: center; gap: 10px; }
.hero-image { position: relative; z-index: 1; overflow: hidden; height: 276px; border: 5px solid #fff; border-radius: 24px; box-shadow: 0 8px 24px rgba(22,50,35,.11); }
.hero-image.image-2 { height: 300px; }
.hero-image img { width: 100%; height: 100%; object-fit: cover; }
.route-line { position: absolute; z-index: 0; left: -70px; right: -55px; bottom: 38px; height: 90px; border: 2px dashed rgba(137, 174, 88, .58); border-left-color: transparent; border-bottom-color: transparent; border-radius: 50%; transform: rotate(-8deg); }
.result-badge { position: absolute; z-index: 2; left: 34%; bottom: -10px; min-width: 310px; min-height: 92px; display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 14px; padding: 15px 18px; background: rgba(255,255,255,.96); border-radius: 22px; box-shadow: 0 14px 32px rgba(26,53,38,.12); }
.result-icon { width: 58px; height: 58px; display: grid; place-items: center; background: #e4f1d7; border-radius: 50%; font-size: 29px; }
.result-badge span:nth-child(2) { display: flex; flex-direction: column; gap: 2px; }
.result-badge small { color: #727975; font-size: 11px; }
.result-badge strong { font-size: 20px; white-space: nowrap; }
.result-badge b { align-self: start; color: #ff8b38; font-size: 22px; }
.type-grid { display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 12px; padding-top: 15px; padding-bottom: 18px; }
.dashboard { display: grid; grid-template-columns: 1.55fr .65fr .68fr; gap: 14px; padding-bottom: 30px; }
.recommendations { min-width: 0; }
.section-header { min-height: 60px; display: flex; align-items: center; justify-content: space-between; gap: 18px; }
.section-header h2 { margin: 0; font-size: 22px; letter-spacing: -.6px; }
.section-header h2::before { content: '●'; margin-right: 10px; color: var(--green-800); font-size: 17px; }
.section-header h2 em { color: var(--green-900); font-style: normal; }
.section-header p { margin: 5px 0 0 27px; color: #6d7470; font-size: 12px; }
.section-header a { color: #5d6661; font-size: 12px; white-space: nowrap; }
.place-grid { display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 13px; }
@media (max-width: 1180px) {
  .hero { grid-template-columns: .9fr 1.1fr; gap: 25px; }
  .result-badge { left: 24%; }
  .type-grid { grid-template-columns: repeat(2, 1fr); }
  .dashboard { grid-template-columns: 1fr 1fr; }
  .recommendations { grid-column: 1 / -1; }
}
@media (max-width: 900px) {
  .hero { grid-template-columns: 1fr; padding-top: 50px; }
  .hero-copy { text-align: center; }
  .hero-actions { justify-content: center; }
  .hero-gallery { margin-top: 10px; }
}
@media (max-width: 700px) {
  .hero-gallery { height: 245px; gap: 5px; }
  .hero-image, .hero-image.image-2 { height: 220px; border-width: 3px; border-radius: 15px; }
  .result-badge { left: 50%; bottom: -12px; min-width: 275px; transform: translateX(-50%); }
  .type-grid, .dashboard { grid-template-columns: 1fr; }
  .place-grid { grid-template-columns: 1fr; }
  .recommendations { grid-column: auto; }
}
@media (max-width: 560px) {
  .hero { padding-top: 36px; }
  .hero-copy h1 { font-size: 39px; letter-spacing: -2px; }
  .hero-actions { flex-direction: column; }
  .hero-gallery { height: 210px; }
  .hero-image, .hero-image.image-2 { height: 180px; }
  .result-badge { min-width: 250px; min-height: 78px; padding: 10px 13px; }
  .result-icon { width: 48px; height: 48px; font-size: 23px; }
  .result-badge strong { font-size: 16px; }
  .section-header h2 { font-size: 19px; }
}
</style>
