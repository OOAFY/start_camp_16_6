<script setup>
import { computed, onMounted, ref, watch } from 'vue'

import ChatButton from '../components/ChatButton.vue'
import CommunityPanel from '../components/CommunityPanel.vue'
import FestivalPanel from '../components/FestivalPanel.vue'
import PlaceCard from '../components/PlaceCard.vue'
import SiteFooter from '../components/SiteFooter.vue'
import TravelTestModal from '../components/TravelTestModal.vue'
import TypeCard from '../components/TypeCard.vue'
import { fetchFestivals, fetchPosts, submitTravelTest } from '../api'
import travelTypeMeta from '../../../data/derived/travel_types.json'
import healingIcon from '../assets/healing.png'
import explorerIcon from '../assets/explorer.png'
import cultureIcon from '../assets/culture.png'
import foodieIcon from '../assets/foodie.png'

const RESULT_KEY = 'localhub-travel-type'
const ONBOARDING_KEY = 'localhub-onboarding-seen'

const showTravelTest = ref(false)
const hasResult = ref(false)
const resultCode = ref('HEALING')
const recommendedPlaces = ref([])
const festivals = ref([])
const posts = ref([])

const heroImages = [
  { alt: '금오산의 푸른 풍경', src: 'https://tong.visitkorea.or.kr/cms/resource/01/3566301_image2_1.jpg' },
  { alt: '고즈넉한 금오서원', src: 'https://tong.visitkorea.or.kr/cms/resource/60/4063260_image2_1.jpg' },
  { alt: '검성지 생태공원', src: 'https://tong.visitkorea.or.kr/cms/resource/08/3032808_image2_1.jpg' }
]

const travelTypes = [
  { code: 'HEALING', name: travelTypeMeta.HEALING.name, description: travelTypeMeta.HEALING.description, keywords: travelTypeMeta.HEALING.keywords, iconSrc: healingIcon, tone: 'green' },
  { code: 'EXPLORER', name: travelTypeMeta.EXPLORER.name, description: travelTypeMeta.EXPLORER.description, keywords: travelTypeMeta.EXPLORER.keywords, iconSrc: explorerIcon, tone: 'blue' },
  { code: 'CULTURE', name: travelTypeMeta.CULTURE.name, description: travelTypeMeta.CULTURE.description, keywords: travelTypeMeta.CULTURE.keywords, iconSrc: cultureIcon, tone: 'purple' },
  { code: 'FOODIE', name: travelTypeMeta.FOODIE.name, description: travelTypeMeta.FOODIE.description, keywords: travelTypeMeta.FOODIE.keywords, iconSrc: foodieIcon, tone: 'orange' }
]

const resultType = computed(() => travelTypes.find((type) => type.code === resultCode.value) || travelTypes[0])
const resultKeywords = computed(() => resultType.value.keywords?.join(' · ') ?? '')

watch(resultCode, () => {
  if (hasResult.value) {
    loadPlaces()
  }
})

onMounted(() => {
  const savedType = sessionStorage.getItem(RESULT_KEY)
  const onboardingSeen = sessionStorage.getItem(ONBOARDING_KEY) === 'true'

  if (savedType) {
    resultCode.value = savedType
    hasResult.value = true
  }

  showTravelTest.value = !onboardingSeen

  loadPlaces()
  loadHomePanelData()
})

function openTravelTest() { showTravelTest.value = true }
function skipTravelTest() { sessionStorage.setItem(ONBOARDING_KEY, 'true'); showTravelTest.value = false }

function completeTravelTest(typeCode) {
  resultCode.value = typeCode
  hasResult.value = true
  showTravelTest.value = false
  sessionStorage.setItem(ONBOARDING_KEY, 'true')
  sessionStorage.setItem(RESULT_KEY, typeCode)
  loadPlaces()
}

function previewType(code) {
  resultCode.value = code
  hasResult.value = true
  loadPlaces()
}

// Helper: map travel type -> option letter (based on travel_test_questions.json)
function _typeToLetter(typeCode) {
  return typeCode === 'HEALING' ? 'A'
    : typeCode === 'EXPLORER' ? 'B'
    : typeCode === 'CULTURE' ? 'C'
    : 'D'
}

// Build answers that force the desired travel type (select the option whose primaryType matches)
function buildAnswersForType(typeCode) {
  const letter = _typeToLetter(typeCode)
  const answers = []
  const requiredCount = 5
  for (let q = 1; q <= requiredCount; q++) {
    answers.push({ questionId: q, optionId: `Q${q}_${letter}` })
  }
  return answers
}

async function loadPlaces() {
  if (!hasResult.value) {
    recommendedPlaces.value = []
    return
  }

  try {
    const payload = { answers: buildAnswersForType(resultCode.value) }
    const data = await submitTravelTest(payload) // returns { travelType, recommendations }
    const items = Array.isArray(data.recommendations) ? data.recommendations : []

    recommendedPlaces.value = items.map(normalizeHomePlace)
  } catch (error) {
    recommendedPlaces.value = []
  }
}

async function loadHomePanelData() {
  try {
    const festivalsResult = await fetchFestivals({ size: 4 })
    festivals.value = Array.isArray(festivalsResult) ? festivalsResult : festivalsResult.items || []
  } catch {
    festivals.value = []
  }

  try {
    const postsResult = await fetchPosts({ size: 4 })
    posts.value = Array.isArray(postsResult) ? postsResult : postsResult.items || []
  } catch {
    posts.value = []
  }
}

function normalizeHomePlace(place) {
  return {
    contentId: place.contentId || place.content_id || '',
    shortTitle: place.title || '',
    title: place.title || '',
    description: place.address || place.region || '',
    imageUrl: place.imageUrl || place.thumbnailUrl || place.thumbnail_url || place.image_url || '',
    category: place.contentType || place.content_type || '',
    matchedKeywords: Array.isArray(place.matchedKeywords) ? place.matchedKeywords : Array.isArray(place.tags) ? place.tags : []
  }
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
              {{ hasResult ? '취향 테스트 다시 하기' : '여행 취향 테스트 시작' }}
              <span>›</span>
            </button>
            <router-link class="btn btn--outline" to="/places">
              지역 먼저 둘러보기 <span>›</span>
            </router-link>
          </div>
        </div>

        <div class="hero-gallery" aria-label="구미·경북 추천 여행지 미리보기">
          <div class="route-line" aria-hidden="true"></div>
          <div
            v-for="(image, index) in heroImages"
            :key="image.src"
            class="hero-image"
            :class="`image-${index + 1}`"
          >
            <img :src="image.src" :alt="image.alt" />
          </div>
          <div class="result-badge">
            <span class="result-icon" :class="resultType.tone">
              <img :src="resultType.iconSrc" :alt="resultType.name" />
            </span>
            <span>
              <small>당신의 여행 성향은</small>
              <strong>{{ resultType.name }}</strong>
            </span>
            <b aria-hidden="true">✦</b>
          </div>
        </div>
      </section>

      <section class="type-grid container" aria-label="여행 취향 유형">
        <TypeCard
          v-for="type in travelTypes"
          :key="type.code"
          :type="type"
          @select="previewType"
        />
      </section>

      <section class="dashboard container">
        <div class="recommendations">
          <header class="section-header">
            <div>
              <h2 v-if="hasResult">
                <em>'{{ resultType.name }}'</em>인 당신을 위한 지역 추천
              </h2>
              <h2 v-else>당신을 위한 지역 추천</h2>
              <p v-if="hasResult">{{ resultKeywords }} 키워드를 바탕으로 골랐어요</p>
              <p v-else>취향 테스트를 완료하면 더 잘 맞는 여행지를 보여드려요</p>
            </div>
            <router-link to="/places">더보기 <span>›</span></router-link>
          </header>
          <div class="place-grid">
            <PlaceCard
              v-for="place in recommendedPlaces"
              :key="place.contentId"
              :place="place"
            />
          </div>
        </div>

        <FestivalPanel :festivals="festivals" />
        <CommunityPanel :posts="posts" />
      </section>
    </main>

    <SiteFooter />
    <ChatButton />
    <TravelTestModal
      v-if="showTravelTest"
      @complete="completeTravelTest"
      @skip="skipTravelTest"
    />
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
.result-icon.green { background: #e4f1d7; color: #3f6b2f; }
.result-icon.blue { background: #e8f2ff; color: #275b92; }
.result-icon.purple { background: #f3ebff; color: #6b3fa3; }
.result-icon.orange { background: #fff2e6; color: #a95f10; }
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