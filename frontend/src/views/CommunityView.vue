<script setup>
import { onMounted, ref } from 'vue'

import { fetchPosts } from '../api'

const posts = ref([])
const isLoading = ref(true)
const errorMessage = ref('')

function formatDate(value) {
  return value ? new Date(value).toLocaleDateString('ko-KR') : ''
}

onMounted(async () => {
  try {
    const data = await fetchPosts({ page: 1, size: 50, sort: 'latest' })
    posts.value = data.items || []
  } catch (error) {
    errorMessage.value = error?.error?.detail || error?.message || '게시글을 불러오지 못했습니다.'
  } finally {
    isLoading.value = false
  }
})
</script>

<template>
  <section class="community-page">
    <div class="page-hero">
      <div class="page-copy">
        <span class="hero-kicker">GUMI · GYEONGBUK COMMUNITY</span>
        <h1>여행 이야기를 나누는<br />커뮤니티</h1>
        <p>구미·경북 여행지 추천, 후기, 일정 이야기를 자유롭게 나눠보세요.</p>
      </div>
      <div class="hero-side-card"><h2>오늘의 이야기</h2><p>실제 여행자들의 추천글과 경험을 살펴보세요.</p></div>
    </div>

    <div class="community-actions">
      <h2>최근 게시글</h2>
      <router-link class="write-button" to="/community/write">글쓰기</router-link>
    </div>

    <p v-if="isLoading" class="state-message">게시글을 불러오는 중입니다.</p>
    <p v-else-if="errorMessage" class="state-message error" role="alert">{{ errorMessage }}</p>
    <p v-else-if="!posts.length" class="state-message">아직 등록된 게시글이 없습니다. 첫 글을 작성해 보세요.</p>
    <div v-else class="community-list">
      <article v-for="post in posts" :key="post.id" class="post-card">
        <div class="post-top">
          <span class="post-chip">{{ post.category }}</span>
          <span class="post-meta">{{ post.nickname }} · {{ formatDate(post.createdAt) }} · 조회 {{ post.viewCount }}</span>
        </div>
        <h3>{{ post.title }}</h3>
        <p>{{ post.content.length > 120 ? `${post.content.slice(0, 120)}…` : post.content }}</p>
        <router-link class="read-more" :to="`/community/${post.id}`">자세히 보기 ›</router-link>
      </article>
    </div>
  </section>
</template>

<style scoped>
.community-page { display: flex; flex-direction: column; gap: 24px; }
.page-hero { display: grid; grid-template-columns: 1.2fr .8fr; gap: 18px; }
.page-copy, .hero-side-card { padding: 28px; border: 1px solid var(--line); border-radius: 24px; background: rgba(255,255,255,.88); box-shadow: var(--shadow); }
.hero-kicker { display: inline-block; margin-bottom: 12px; color: var(--green-700); font-size: 11px; font-weight: 850; letter-spacing: 1.8px; }
.page-copy h1 { margin: 0; color: var(--navy); font-size: clamp(28px, 3vw, 40px); line-height: 1.2; }
.community-actions { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-top: 4px; }
.community-actions h2 { margin: 0; color: var(--navy); font-size: 20px; }
.write-button { display: inline-flex; padding: 10px 16px; border-radius: 999px; background: var(--green-900); color: #fff; font-size: 13px; font-weight: 700; }
.community-list { display: grid; gap: 14px; }
.post-card { padding: 20px; border: 1px solid var(--line); border-radius: 18px; background: #fff; box-shadow: 0 8px 22px rgba(35,52,43,.06); }
.post-top { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-bottom: 10px; }
.post-chip { padding: 6px 10px; border-radius: 999px; background: var(--green-100); color: var(--green-900); font-size: 11px; font-weight: 800; }
.post-meta { color: #6b736f; font-size: 12px; }
.post-card h3 { margin: 0 0 8px; color: var(--navy); }
.post-card p { margin: 0 0 10px; color: #5d665e; line-height: 1.6; white-space: pre-line; }
.read-more { color: var(--green-900); font-weight: 700; }
.state-message { padding: 28px; text-align: center; color: #66736c; background: #fff; border-radius: 18px; }
.state-message.error { color: #9b302c; background: #fff0ef; }
@media (max-width: 700px) { .page-hero { grid-template-columns: 1fr; } .post-top { align-items: flex-start; flex-direction: column; } }
</style>
