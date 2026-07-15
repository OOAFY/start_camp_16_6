<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { deletePost, fetchPostDetail } from '../api'

const route = useRoute()
const router = useRouter()
const post = ref(null)
const password = ref('')
const showDelete = ref(false)
const isDeleting = ref(false)
const errorMessage = ref('')

function formatDate(value) {
  return value ? new Date(value).toLocaleString('ko-KR') : ''
}

function apiErrorMessage(error) {
  return error?.error?.detail || error?.message || '요청을 처리하지 못했습니다.'
}

onMounted(async () => {
  try {
    post.value = await fetchPostDetail(route.params.id)
  } catch (error) {
    errorMessage.value = apiErrorMessage(error)
  }
})

async function removePost() {
  if (!password.value || isDeleting.value) return
  errorMessage.value = ''
  isDeleting.value = true
  try {
    await deletePost(route.params.id, password.value)
    await router.push('/community')
  } catch (error) {
    errorMessage.value = apiErrorMessage(error)
  } finally {
    isDeleting.value = false
  }
}
</script>

<template>
  <section class="detail-page">
    <div v-if="post" class="detail-card">
      <span class="post-chip">{{ post.category }}</span>
      <h1>{{ post.title }}</h1>
      <p class="meta">{{ post.nickname }} · {{ formatDate(post.createdAt) }} · 조회 {{ post.viewCount }}</p>
      <div class="content">{{ post.content }}</div>

      <div class="detail-actions">
        <router-link class="list-button" to="/community">목록</router-link>
        <router-link class="edit-button" :to="`/community/${post.id}/edit`">수정</router-link>
        <button class="delete-button" type="button" @click="showDelete = !showDelete">삭제</button>
      </div>

      <form v-if="showDelete" class="delete-form" @submit.prevent="removePost">
        <label for="delete-password">등록할 때 사용한 비밀번호를 입력하세요.</label>
        <div>
          <input id="delete-password" v-model="password" type="password" maxlength="100" required />
          <button type="submit" :disabled="isDeleting">{{ isDeleting ? '삭제 중…' : '삭제 확인' }}</button>
        </div>
      </form>
      <p v-if="errorMessage" class="error-message" role="alert">{{ errorMessage }}</p>
    </div>
    <div v-else class="detail-card state-message">
      <p v-if="errorMessage" class="error-message" role="alert">{{ errorMessage }}</p>
      <p v-else>게시글을 불러오는 중입니다.</p>
      <router-link v-if="errorMessage" to="/community">목록으로 돌아가기</router-link>
    </div>
  </section>
</template>

<style scoped>
.detail-page { display: flex; justify-content: center; }
.detail-card { width: 100%; max-width: 860px; padding: 28px; border: 1px solid var(--line); border-radius: 24px; background: rgba(255,255,255,.92); box-shadow: var(--shadow); }
.post-chip { display: inline-block; padding: 6px 10px; border-radius: 999px; background: var(--green-100); color: var(--green-900); font-size: 11px; font-weight: 800; }
.detail-card h1 { margin: 14px 0 8px; color: var(--navy); font-size: clamp(24px, 2.4vw, 32px); }
.meta { color: #6b736f; font-size: 13px; }
.content { min-height: 180px; margin-top: 18px; padding-top: 18px; border-top: 1px solid var(--line); color: #4d554f; line-height: 1.8; white-space: pre-wrap; }
.detail-actions { display: flex; justify-content: flex-end; gap: 9px; margin-top: 24px; }
.detail-actions a, .detail-actions button { padding: 9px 14px; border: 0; border-radius: 10px; font: inherit; font-weight: 700; cursor: pointer; }
.list-button { color: #4f5a54; background: #edf1ee; }
.edit-button { color: #fff; background: var(--green-900); }
.delete-button { color: #a3312d; background: #fff0ef; }
.delete-form { margin-top: 15px; padding: 16px; background: #fff7f6; border-radius: 12px; }
.delete-form label { display: block; margin-bottom: 9px; color: #633b38; font-size: 13px; font-weight: 700; }
.delete-form div { display: flex; gap: 8px; }
.delete-form input { flex: 1; min-width: 0; padding: 10px 12px; border: 1px solid #dfc2bf; border-radius: 9px; }
.delete-form button { padding: 9px 13px; color: #fff; background: #a63b35; border: 0; border-radius: 9px; font-weight: 700; }
.error-message { margin-top: 12px; padding: 10px 12px; color: #9b302c; background: #fff0ef; border-radius: 10px; font-size: 13px; }
.state-message { text-align: center; color: #66736c; }
button:disabled { opacity: .55; cursor: default; }
</style>
