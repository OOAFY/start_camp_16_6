<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { createPost, fetchPostDetail, updatePost } from '../api'

const route = useRoute()
const router = useRouter()
const isEdit = computed(() => route.name === 'CommunityEdit')
const isLoading = ref(false)
const isSubmitting = ref(false)
const errorMessage = ref('')
const form = reactive({
  title: '',
  category: '여행',
  nickname: '익명',
  content: '',
  password: ''
})

function apiErrorMessage(error) {
  return error?.error?.detail || error?.message || '요청을 처리하지 못했습니다.'
}

onMounted(async () => {
  if (!isEdit.value) return
  isLoading.value = true
  try {
    const post = await fetchPostDetail(route.params.id)
    form.title = post.title
    form.category = post.category
    form.nickname = post.nickname
    form.content = post.content
  } catch (error) {
    errorMessage.value = apiErrorMessage(error)
  } finally {
    isLoading.value = false
  }
})

async function submitPost() {
  if (isSubmitting.value) return
  errorMessage.value = ''
  isSubmitting.value = true

  try {
    const payload = {
      title: form.title.trim(),
      category: form.category,
      nickname: form.nickname.trim(),
      content: form.content.trim(),
      // 서버는 이 값을 응답에 포함하지 않고 수정·삭제 검증에만 사용합니다.
      password: form.password
    }
    const post = isEdit.value
      ? await updatePost(route.params.id, payload)
      : await createPost(payload)
    await router.push(`/community/${post.id}`)
  } catch (error) {
    errorMessage.value = apiErrorMessage(error)
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <section class="write-page">
    <div class="write-card">
      <span class="hero-kicker">GUMI · GYEONGBUK COMMUNITY</span>
      <h1>{{ isEdit ? '게시글 수정하기' : '게시글 작성하기' }}</h1>
      <p>{{ isEdit ? '등록할 때 사용한 비밀번호가 일치해야 수정됩니다.' : '여행 경험이나 추천글을 남겨보세요.' }}</p>

      <p v-if="isLoading" class="status-message">게시글을 불러오는 중입니다.</p>
      <form v-else class="write-form" @submit.prevent="submitPost">
        <label>
          제목
          <input v-model="form.title" type="text" maxlength="200" placeholder="제목을 입력하세요" required />
        </label>

        <div class="form-row">
          <label>
            카테고리
            <select v-model="form.category" required>
              <option>여행</option>
              <option>맛집</option>
              <option>축제</option>
              <option>생활</option>
              <option>자유</option>
            </select>
          </label>
          <label>
            닉네임
            <input v-model="form.nickname" type="text" maxlength="50" placeholder="익명" required />
          </label>
        </div>

        <label>
          내용
          <textarea v-model="form.content" rows="8" placeholder="내용을 입력하세요" required></textarea>
        </label>

        <label>
          수정용 비밀번호
          <input
            v-model="form.password"
            type="password"
            maxlength="100"
            autocomplete="new-password"
            :placeholder="isEdit ? '등록할 때 사용한 비밀번호' : '수정·삭제할 때 사용할 비밀번호'"
            required
          />
          <small>비밀번호는 게시글 응답이나 화면에 표시되지 않습니다.</small>
        </label>

        <p v-if="errorMessage" class="error-message" role="alert">{{ errorMessage }}</p>
        <div class="form-actions">
          <router-link class="cancel-button" :to="isEdit ? `/community/${route.params.id}` : '/community'">취소</router-link>
          <button class="btn btn--primary" type="submit" :disabled="isSubmitting">
            {{ isSubmitting ? '처리 중…' : (isEdit ? '게시글 수정' : '게시글 등록') }}
          </button>
        </div>
      </form>
    </div>
  </section>
</template>

<style scoped>
.write-page { display: flex; justify-content: center; }
.write-card { width: 100%; max-width: 760px; padding: 28px; border: 1px solid var(--line); border-radius: 24px; background: rgba(255,255,255,.92); box-shadow: var(--shadow); }
.hero-kicker { display: inline-block; margin-bottom: 12px; color: var(--green-700); font-size: 11px; font-weight: 850; letter-spacing: 1.8px; }
.write-card h1 { margin: 0; color: var(--navy); font-size: clamp(24px, 2.4vw, 30px); }
.write-card > p { margin: 8px 0 20px; color: #5d665e; }
.write-form { display: flex; flex-direction: column; gap: 14px; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.write-form label { display: flex; flex-direction: column; gap: 8px; color: var(--navy); font-weight: 700; }
.write-form input, .write-form select, .write-form textarea { padding: 12px 14px; border: 1px solid var(--line); border-radius: 12px; background: #fff; font: inherit; }
.write-form textarea { resize: vertical; }
.write-form small { color: #737b76; font-size: 11px; font-weight: 400; }
.form-actions { display: flex; justify-content: flex-end; align-items: center; gap: 12px; margin-top: 8px; }
.cancel-button { padding: 11px 16px; color: #5d665e; font-weight: 700; }
.error-message { margin: 0; padding: 10px 12px; color: #9b302c; background: #fff0ef; border-radius: 10px; font-size: 13px; }
.status-message { color: #66736c; }
button:disabled { opacity: .55; cursor: default; }
@media (max-width: 560px) { .form-row { grid-template-columns: 1fr; } .write-card { padding: 22px 18px; } }
</style>
