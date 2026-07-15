<template>
  <section class="festivals-page">
    <div class="page-hero">
      <div class="page-copy">
        <span class="hero-kicker">GUMI · GYEONGBUK FESTIVALS</span>
        <h1>구미·경북의 축제와<br />이벤트를 만나보세요</h1>
        <p class="hero-description">
          달력으로 축제 일정을 살펴보고,<br />지역별 행사 정보와 추천 축제를 한눈에 확인해보세요.
        </p>
        <div class="hero-summary" aria-label="현재 선택한 달의 축제 요약">
          <div>
            <strong>{{ visibleFestivals.length }}</strong>
            <span>{{ visibleMonthLabel }} 축제</span>
          </div>
          <span class="summary-divider" aria-hidden="true"></span>
          <div>
            <strong>{{ visibleRegionCount }}</strong>
            <span>만날 수 있는 지역</span>
          </div>
        </div>
      </div>

      <div class="hero-side-card">
        <div class="recommend-heading">
          <div>
            <span class="recommend-kicker">MONTHLY PICK</span>
            <h2>이번 달의 추천</h2>
          </div>
          <span class="recommend-month">{{ visibleMonthLabel }}</span>
        </div>

        <div v-if="isLoading" class="recommend-empty">추천 축제를 불러오는 중이에요.</div>
        <div v-else-if="recommendedFestivals.length" class="recommend-grid">
          <button
            v-for="festival in recommendedFestivals"
            :key="getFestivalId(festival)"
            class="recommend-card"
            type="button"
            @click="openFestivalDetail(festival)"
          >
            <img
              v-if="getFestivalImage(festival)"
              :src="getFestivalImage(festival)"
              :alt="`${festival.title} 이미지`"
              loading="lazy"
            />
            <div v-else class="image-placeholder">FESTIVAL</div>
            <span class="recommend-overlay">
              <small>{{ getFestivalRegion(festival) }}</small>
              <strong>{{ festival.title }}</strong>
            </span>
          </button>
        </div>
        <div v-else class="recommend-empty">{{ visibleMonthLabel }}에는 추천할 축제가 아직 없어요.</div>
      </div>
    </div>

    <div class="calendar-card">
      <div class="section-header">
        <div>
          <h2>축제 캘린더</h2>
          <p>달을 이동하면 해당 월에 열리는 축제만 아래에 표시됩니다.</p>
        </div>
      </div>

      <div v-if="isLoading" class="status-card">축제 정보를 불러오는 중입니다...</div>
      <div v-else-if="errorMessage" class="status-card error">{{ errorMessage }}</div>
      <FullCalendar v-else :options="calendarOptions" />
    </div>

    <div class="list-heading">
      <div>
        <span class="list-kicker">{{ visibleMonthLabel }}</span>
        <h2>이달의 축제</h2>
      </div>
      <span class="festival-count">총 {{ visibleFestivals.length }}개</span>
    </div>

    <div v-if="isLoading" class="status-card">축제 데이터를 정리하고 있어요.</div>
    <div v-else-if="errorMessage" class="status-card error">{{ errorMessage }}</div>
    <div v-else-if="visibleFestivals.length === 0" class="status-card">
      {{ visibleMonthLabel }}에 진행되는 축제가 없습니다.
    </div>
    <div v-else class="festival-list">
      <button
        v-for="festival in visibleFestivals"
        :key="getFestivalId(festival)"
        class="festival-card"
        type="button"
        @click="openFestivalDetail(festival)"
      >
        <div class="festival-content">
          <span class="festival-chip">{{ getFestivalRegion(festival) }}</span>
          <h3>{{ festival.title }}</h3>
          <p class="festival-address">{{ getFestivalAddress(festival) }}</p>
        </div>

        <div class="festival-meta">
          <span class="meta-label">일정</span>
          <strong>{{ getFestivalDateLabel(festival) }}</strong>
          <span class="meta-label contact-label">연락처</span>
          <strong>{{ getFestivalTelephone(festival) || '미등록' }}</strong>
        </div>
      </button>
    </div>

    <Teleport to="body">
      <div v-if="selectedFestival" class="modal-backdrop" @click.self="closeFestivalDetail">
        <section class="detail-modal" role="dialog" aria-modal="true" aria-labelledby="festival-detail-title">
          <button class="modal-close" type="button" aria-label="상세 정보 닫기" @click="closeFestivalDetail">×</button>
          <div class="detail-image">
            <img
              v-if="getFestivalImage(selectedFestival)"
              :src="getFestivalImage(selectedFestival)"
              :alt="`${selectedFestival.title} 이미지`"
            />
            <div v-else class="image-placeholder">GUMI · GYEONGBUK FESTIVAL</div>
          </div>
          <div class="detail-body">
            <span class="festival-chip">{{ getFestivalRegion(selectedFestival) }}</span>
            <h2 id="festival-detail-title">{{ selectedFestival.title }}</h2>
            <dl class="detail-list">
              <div><dt>일정</dt><dd>{{ getFestivalDateLabel(selectedFestival) }}</dd></div>
              <div><dt>주소</dt><dd>{{ getFestivalAddress(selectedFestival) }}</dd></div>
              <div><dt>연락처</dt><dd>{{ getFestivalTelephone(selectedFestival) || '연락처 미등록' }}</dd></div>
            </dl>
          </div>
        </section>
      </div>
    </Teleport>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import FullCalendar from '@fullcalendar/vue3'
import dayGridPlugin from '@fullcalendar/daygrid'
import { fetchFestivals } from '../api'

const festivals = ref([])
const isLoading = ref(false)
const errorMessage = ref('')
const visibleMonthStart = ref(startOfMonth(new Date()))
const selectedFestival = ref(null)

function normalizeDate(value) {
  if (!value) return null
  const text = String(value).trim()
  if (!text) return null
  if (/^\d{4}-\d{2}-\d{2}$/.test(text)) return text
  if (/^\d{4}\.\d{2}\.\d{2}$/.test(text)) return text.replace(/\./g, '-')
  return text
}

function toLocalDate(value) {
  const normalized = normalizeDate(value)
  if (!normalized) return null
  const match = normalized.match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (!match) return null
  return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]))
}

function startOfMonth(value) {
  return new Date(value.getFullYear(), value.getMonth(), 1)
}

function endOfMonth(value) {
  return new Date(value.getFullYear(), value.getMonth() + 1, 0, 23, 59, 59, 999)
}

function addOneDay(value) {
  const date = toLocalDate(value)
  if (!date) return undefined
  date.setDate(date.getDate() + 1)
  return [date.getFullYear(), String(date.getMonth() + 1).padStart(2, '0'), String(date.getDate()).padStart(2, '0')].join('-')
}

function getValue(festival, keys) {
  for (const key of keys) {
    const value = festival?.[key]
    if (value !== undefined && value !== null && value !== '') return value
  }
  return null
}

function getFestivalId(festival) {
  return String(getValue(festival, ['contentId', 'content_id', 'id']) || `${festival.title}-${getFestivalStart(festival)}`)
}

function getFestivalStart(festival) {
  return normalizeDate(getValue(festival, ['startDate', 'start_date', 'eventStartDate']))
}

function getFestivalEnd(festival) {
  return normalizeDate(getValue(festival, ['endDate', 'end_date', 'eventEndDate']))
}

function formatDate(value) {
  const normalized = normalizeDate(value)
  return normalized ? normalized.replace(/-/g, '.') : '일정 미정'
}

function getFestivalDateLabel(festival) {
  const start = getFestivalStart(festival)
  const end = getFestivalEnd(festival)
  if (!start) return '일정 미정'
  return end && end !== start ? `${formatDate(start)} ~ ${formatDate(end)}` : formatDate(start)
}

function getFestivalRegion(festival) {
  return getValue(festival, ['region', 'location']) || '축제'
}

function getFestivalAddress(festival) {
  const base = getValue(festival, ['address', 'addr'])
  const detail = getValue(festival, ['detailAddress', 'detail_address'])
  return [base, detail].filter(Boolean).join(' ') || '주소 정보 미등록'
}

function getFestivalTelephone(festival) {
  return getValue(festival, ['telephone', 'tel'])
}

function getFestivalImage(festival) {
  return getValue(festival, ['imageUrl', 'image_url', 'thumbnailUrl', 'thumbnail_url'])
}

function overlapsVisibleMonth(festival) {
  const start = toLocalDate(getFestivalStart(festival))
  if (!start) return false
  const end = toLocalDate(getFestivalEnd(festival)) || start
  return end >= visibleMonthStart.value && start <= endOfMonth(visibleMonthStart.value)
}

const visibleMonthLabel = computed(() =>
  new Intl.DateTimeFormat('ko-KR', { year: 'numeric', month: 'long' }).format(visibleMonthStart.value)
)

const visibleFestivals = computed(() =>
  festivals.value.filter(overlapsVisibleMonth).sort((a, b) => getFestivalStart(a).localeCompare(getFestivalStart(b)))
)

const recommendedFestivals = computed(() => visibleFestivals.value.slice(0, 2))

const visibleRegionCount = computed(() =>
  new Set(visibleFestivals.value.map(getFestivalRegion).filter((region) => region && region !== '축제')).size
)

const calendarColors = [
  { background: '#168152', border: '#0f6842' },
  { background: '#2878b5', border: '#1d6092' },
  { background: '#d06b32', border: '#a95025' },
  { background: '#7b5bb2', border: '#624692' },
  { background: '#c34f72', border: '#9e3a59' },
  { background: '#218b8a', border: '#176e6d' }
]

function getCalendarColor(festival) {
  const id = getFestivalId(festival)
  let hash = 0
  for (let index = 0; index < id.length; index += 1) {
    hash = ((hash << 5) - hash + id.charCodeAt(index)) | 0
  }
  return calendarColors[Math.abs(hash) % calendarColors.length]
}

const calendarEvents = computed(() =>
  festivals.value
    .map((festival) => {
      const start = getFestivalStart(festival)
      if (!start) return null
      const color = getCalendarColor(festival)
      return {
        id: getFestivalId(festival),
        title: festival.title || '축제',
        start,
        // FullCalendar의 종료일은 exclusive이므로 실제 종료일 다음 날을 전달합니다.
        end: addOneDay(getFestivalEnd(festival) || start),
        backgroundColor: color.background,
        borderColor: color.border,
        textColor: '#fff',
        extendedProps: { festival }
      }
    })
    .filter(Boolean)
)

function handleDatesSet(info) {
  visibleMonthStart.value = startOfMonth(info.view.currentStart)
}

function openFestivalDetail(festival) {
  selectedFestival.value = festival
  document.body.style.overflow = 'hidden'
}

function closeFestivalDetail() {
  selectedFestival.value = null
  document.body.style.overflow = ''
}

function handleKeydown(event) {
  if (event.key === 'Escape' && selectedFestival.value) closeFestivalDetail()
}

const calendarOptions = computed(() => ({
  plugins: [dayGridPlugin],
  initialView: 'dayGridMonth',
  locale: 'ko',
  contentHeight: 590,
  expandRows: true,
  fixedWeekCount: false,
  dayMaxEvents: 3,
  headerToolbar: { left: 'prev,next', center: 'title', right: 'today' },
  buttonText: { today: '오늘' },
  eventDisplay: 'block',
  events: calendarEvents.value,
  datesSet: handleDatesSet,
  eventClick: ({ event }) => openFestivalDetail(event.extendedProps.festival)
}))

onMounted(async () => {
  window.addEventListener('keydown', handleKeydown)
  isLoading.value = true
  errorMessage.value = ''
  try {
    const data = await fetchFestivals()
    festivals.value = Array.isArray(data) ? data : data?.items || []
  } catch (err) {
    errorMessage.value = err?.message || '축제 정보를 불러오지 못했습니다.'
  } finally {
    isLoading.value = false
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeydown)
  document.body.style.overflow = ''
})
</script>

<style scoped>
.festivals-page { display: flex; flex-direction: column; gap: 24px; }
.page-hero { display: grid; grid-template-columns: 1.05fr .95fr; gap: 18px; }
.page-copy, .hero-side-card, .calendar-card { padding: 28px; border: 1px solid var(--line); border-radius: 24px; background: rgba(255,255,255,.92); box-shadow: var(--shadow); }
.hero-kicker, .recommend-kicker, .list-kicker { display: inline-block; color: var(--green-700); font-size: 11px; font-weight: 850; letter-spacing: 1.5px; }
.hero-kicker { margin-bottom: 12px; }
.page-copy h1 { margin: 0; color: var(--navy); font-size: clamp(28px,3vw,40px); line-height: 1.2; }
.page-copy { display: flex; flex-direction: column; }
.page-copy p { margin: 14px 0 0; color: #5d665e; font-size: 15px; line-height: 1.75; }
.hero-summary { display: flex; align-items: center; gap: 22px; margin-top: auto; padding-top: 22px; }
.hero-summary div { display: grid; grid-template-columns: auto 1fr; gap: 3px 8px; align-items: baseline; }
.hero-summary strong { grid-row: 1 / 3; color: var(--green-800); font-size: 28px; line-height: 1; }
.hero-summary span:not(.summary-divider) { color: #6c776f; font-size: 12px; font-weight: 700; }
.summary-divider { width: 1px; height: 30px; background: #dfe6e1; }
.hero-side-card { min-width: 0; }
.recommend-heading, .list-heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.recommend-heading h2, .section-header h2, .list-heading h2 { margin: 4px 0 0; color: var(--navy); font-size: 20px; }
.recommend-month, .festival-count { padding: 7px 11px; border-radius: 999px; background: var(--green-100); color: var(--green-900); font-size: 12px; font-weight: 800; white-space: nowrap; }
.recommend-grid { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 10px; margin-top: 16px; }
.recommend-card { position: relative; min-width: 0; height: 148px; padding: 0; overflow: hidden; border: 0; border-radius: 16px; background: #dfe9e2; color: #fff; cursor: pointer; text-align: left; }
.recommend-card img { width: 100%; height: 100%; object-fit: cover; transition: transform .25s ease; }
.recommend-card:hover img { transform: scale(1.04); }
.recommend-overlay { position: absolute; inset: auto 0 0; display: flex; flex-direction: column; gap: 3px; padding: 28px 13px 12px; background: linear-gradient(transparent,rgba(14,31,23,.88)); }
.recommend-overlay small { font-size: 11px; opacity: .85; }
.recommend-overlay strong { overflow: hidden; font-size: 14px; line-height: 1.35; text-overflow: ellipsis; white-space: nowrap; }
.recommend-empty { display: grid; min-height: 148px; margin-top: 16px; place-items: center; border-radius: 16px; background: #f4f7f4; color: #778079; font-size: 13px; text-align: center; }
.image-placeholder { display: grid; width: 100%; height: 100%; place-items: center; background: linear-gradient(135deg,#b9d4c3,#6c9f7f); color: rgba(255,255,255,.82); font-size: 11px; font-weight: 800; letter-spacing: 1.2px; }
.section-header { margin-bottom: 22px; }
.section-header p { margin: 6px 0 0; color: #6b736f; font-size: 14px; }
.status-card { padding: 20px; border: 1px solid var(--line); border-radius: 18px; background: #fff; color: #5d665e; text-align: center; }
.status-card.error { color: #b42318; }
.calendar-card :deep(.fc) { font-family: inherit; color: #34443a; }
.calendar-card :deep(.fc-header-toolbar) { margin-bottom: 20px; padding: 12px 14px; border-radius: 16px; background: #f5f8f5; }
.calendar-card :deep(.fc-toolbar-chunk) { display: flex; align-items: center; gap: 6px; }
.calendar-card :deep(.fc-toolbar-title) { color: var(--navy); font-size: clamp(18px,2vw,23px); font-weight: 850; }
.calendar-card :deep(.fc-button) { min-height: 36px; padding: 7px 12px; border: 1px solid #d6e2da !important; border-radius: 10px !important; background: #fff !important; box-shadow: none !important; color: var(--green-800) !important; font-size: 13px !important; font-weight: 750 !important; }
.calendar-card :deep(.fc-button:hover), .calendar-card :deep(.fc-button:focus) { border-color: var(--green-700) !important; background: var(--green-100) !important; }
.calendar-card :deep(.fc-prev-button), .calendar-card :deep(.fc-next-button) { width: 38px; padding: 0 !important; }
.calendar-card :deep(.fc-scrollgrid) { overflow: hidden; border: 1px solid #e1e8e3; border-radius: 16px; }
.calendar-card :deep(.fc-daygrid-body), .calendar-card :deep(.fc-daygrid-body table) { height: 100% !important; }
.calendar-card :deep(.fc-daygrid-body tr) { height: 1px; }
.calendar-card :deep(.fc-daygrid-day-frame) { min-height: 100%; }
.calendar-card :deep(.fc-col-header-cell) { border-color: #e7ece8; background: #f8faf8; }
.calendar-card :deep(.fc-col-header-cell-cushion) { padding: 11px 4px; color: #536158; font-size: 12px; font-weight: 800; text-decoration: none; }
.calendar-card :deep(.fc-daygrid-day), .calendar-card :deep(td), .calendar-card :deep(th) { border-color: #e7ece8; }
.calendar-card :deep(.fc-daygrid-day-number) { padding: 8px; color: #536158; font-size: 12px; text-decoration: none; }
.calendar-card :deep(.fc-day-today) { background: #f0f8f3 !important; }
.calendar-card :deep(.fc-day-today .fc-daygrid-day-number) { margin: 5px; padding: 3px 7px; border-radius: 999px; background: var(--green-800); color: #fff; }
.calendar-card :deep(.fc-event) { margin: 2px 4px; padding: 3px 6px; overflow: hidden; border-width: 0 0 0 3px; border-style: solid; border-radius: 6px; color: #fff; cursor: pointer; font-size: 11px; }
.list-heading { margin-top: 4px; padding: 0 4px; }
.festival-list { display: grid; gap: 14px; }
.festival-card { display: flex; width: 100%; align-items: center; justify-content: space-between; gap: 20px; padding: 20px; border: 1px solid var(--line); border-radius: 18px; background: #fff; box-shadow: 0 8px 22px rgba(35,52,43,.06); color: inherit; cursor: pointer; font: inherit; text-align: left; transition: transform .18s ease,border-color .18s ease,box-shadow .18s ease; }
.festival-card:hover { transform: translateY(-2px); border-color: #a8cbb4; box-shadow: 0 12px 28px rgba(35,52,43,.1); }
.festival-content { flex: 1; min-width: 0; }
.festival-chip { display: inline-block; margin-bottom: 8px; padding: 6px 10px; border-radius: 999px; background: var(--green-100); color: var(--green-900); font-size: 11px; font-weight: 800; }
.festival-card h3 { margin: 0 0 8px; color: var(--navy); font-size: 20px; }
.festival-address { margin: 0; color: #59655d; font-size: 14px; line-height: 1.6; }
.festival-meta { display: grid; grid-template-columns: auto auto; gap: 4px 12px; align-items: baseline; color: #536158; font-size: 13px; }
.festival-meta .meta-label { color: #8a938d; font-size: 11px; font-weight: 700; }
.festival-meta .contact-label { grid-column: 1; }
.festival-meta strong { font-weight: 700; }
.modal-backdrop { position: fixed; z-index: 1000; inset: 0; display: grid; padding: 24px; place-items: center; background: rgba(15,28,21,.55); backdrop-filter: blur(4px); }
.detail-modal { position: relative; width: min(520px,100%); max-height: calc(100vh - 48px); overflow: auto; border-radius: 24px; background: #fff; box-shadow: 0 28px 80px rgba(0,0,0,.24); }
.modal-close { position: absolute; z-index: 1; top: 14px; right: 14px; width: 36px; height: 36px; border: 0; border-radius: 50%; background: rgba(255,255,255,.92); color: #24332a; cursor: pointer; font-size: 25px; line-height: 1; }
.detail-image { height: 240px; overflow: hidden; border-radius: 24px 24px 0 0; }
.detail-image img { width: 100%; height: 100%; object-fit: cover; }
.detail-body { padding: 26px 28px 30px; }
.detail-body h2 { margin: 3px 0 22px; color: var(--navy); font-size: 25px; }
.detail-list { display: grid; gap: 0; margin: 0; }
.detail-list div { display: grid; grid-template-columns: 68px 1fr; gap: 12px; padding: 13px 0; border-top: 1px solid #edf0ed; }
.detail-list dt { color: #879089; font-size: 13px; font-weight: 750; }
.detail-list dd { margin: 0; color: #3e4a42; font-size: 14px; line-height: 1.55; }
@media (max-width: 700px) {
  .page-hero { grid-template-columns: 1fr; }
  .page-copy, .hero-side-card, .calendar-card { padding: 20px; }
  .hero-summary { margin-top: 24px; }
  .calendar-card :deep(.fc-header-toolbar) { display: grid; grid-template-columns: 1fr auto 1fr; gap: 8px; padding: 10px; }
  .calendar-card :deep(.fc-toolbar-title) { font-size: 17px; text-align: center; }
  .calendar-card :deep(.fc-toolbar-chunk:last-child) { justify-content: flex-end; }
  .festival-card { flex-direction: column; align-items: stretch; }
  .festival-meta { grid-template-columns: 54px 1fr; }
}
@media (max-width: 430px) {
  .hero-summary { align-items: flex-start; gap: 14px; }
  .hero-summary div { display: flex; flex-direction: column; }
  .hero-summary strong { font-size: 24px; }
  .recommend-grid { grid-template-columns: 1fr; }
  .recommend-card { height: 160px; }
  .calendar-card :deep(.fc-header-toolbar) { grid-template-columns: 1fr 1fr; }
  .calendar-card :deep(.fc-toolbar-chunk:nth-child(2)) { grid-column: 1 / -1; grid-row: 1; justify-content: center; }
  .calendar-card :deep(.fc-toolbar-chunk:first-child) { grid-row: 2; }
  .calendar-card :deep(.fc-toolbar-chunk:last-child) { grid-row: 2; }
  .modal-backdrop { padding: 12px; }
  .detail-image { height: 190px; }
  .detail-body { padding: 22px 20px 25px; }
}
</style>
