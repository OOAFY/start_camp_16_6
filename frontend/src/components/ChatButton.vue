<script setup>
import { nextTick, ref } from 'vue'

import { sendChat } from '../api'

const isOpen = ref(false)
const input = ref('')
const isSending = ref(false)
const messages = ref([
  {
    role: 'assistant',
    content: '안녕하세요! 구미·경북 여행지와 지역 정보를 안내해 드릴게요.',
    references: [],
    isIntro: true
  }
])
const messageList = ref(null)

function toggleChat() {
  isOpen.value = !isOpen.value
  if (isOpen.value) nextTick(() => scrollToBottom())
}

function scrollToBottom() {
  if (messageList.value) messageList.value.scrollTop = messageList.value.scrollHeight
}

function referenceLink(reference) {
  if (reference.type === 'place') {
    return { path: '/places', query: { selected: reference.id } }
  }
  if (reference.type === 'festival') {
    return { path: '/festivals', query: { selected: reference.id } }
  }
  return { path: `/community/${reference.id}` }
}

async function submitMessage() {
  const content = input.value.trim()
  if (!content || isSending.value) return

  // 현재 질문을 제외한 실제 대화만 API history로 전달합니다.
  const history = messages.value
    .filter((message) => !message.isError && !message.isIntro)
    .map(({ role, content: messageContent }) => ({ role, content: messageContent }))

  messages.value.push({ role: 'user', content, references: [] })
  input.value = ''
  isSending.value = true
  await nextTick()
  scrollToBottom()

  try {
    const data = await sendChat(content, history)
    messages.value.push({
      role: 'assistant',
      content: data.answer,
      references: data.references || []
    })
  } catch (error) {
    messages.value.push({
      role: 'assistant',
      content: error?.error?.detail || error?.message || '답변을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.',
      references: [],
      isError: true
    })
  } finally {
    isSending.value = false
    await nextTick()
    scrollToBottom()
  }
}
</script>

<template>
  <aside v-if="isOpen" class="chat-panel" aria-label="LocalHub AI 챗봇">
    <header class="chat-header">
      <div>
        <strong>LocalHub AI</strong>
        <small>구미·경북 여행 도우미</small>
      </div>
      <button type="button" class="close-button" aria-label="챗봇 닫기" @click="toggleChat">×</button>
    </header>

    <div ref="messageList" class="message-list" aria-live="polite">
      <article
        v-for="(message, index) in messages"
        :key="index"
        class="message"
        :class="[message.role, { error: message.isError }]"
      >
        <p>{{ message.content }}</p>
        <nav v-if="message.references?.length" class="references" aria-label="답변 관련 링크">
          <router-link
            v-for="reference in message.references"
            :key="`${reference.type}-${reference.id}`"
            :to="referenceLink(reference)"
            @click="isOpen = false"
          >
            {{ reference.title }} →
          </router-link>
        </nav>
      </article>
      <div v-if="isSending" class="message assistant loading">답변을 작성하고 있어요<span>…</span></div>
    </div>

    <form class="chat-form" @submit.prevent="submitMessage">
      <label class="sr-only" for="chat-message">챗봇에게 보낼 메시지</label>
      <textarea
        id="chat-message"
        v-model="input"
        rows="1"
        maxlength="1000"
        placeholder="여행지를 물어보세요"
        :disabled="isSending"
        @keydown.enter.exact.prevent="submitMessage"
      ></textarea>
      <button type="submit" :disabled="isSending || !input.trim()">전송</button>
    </form>
  </aside>

  <button
    class="chat-button"
    type="button"
    :aria-expanded="isOpen"
    aria-label="LocalHub AI 챗봇 열기"
    @click="toggleChat"
  >
    <span class="spark" aria-hidden="true">✦</span>
    <span class="chat-icon" aria-hidden="true">•••</span>
    <span class="chat-label">LocalHub AI</span>
  </button>
</template>

<style scoped>
.chat-button { position: fixed; z-index: 110; right: 30px; bottom: 28px; width: 70px; height: 70px; display: grid; place-items: center; color: #fff; background: var(--green-900); border: 5px solid rgba(255,255,255,.86); border-radius: 50%; box-shadow: 0 12px 26px rgba(7,92,58,.24); cursor: pointer; }
.chat-icon { width: 33px; height: 27px; display: grid; place-items: center; border: 2px solid #fff; border-radius: 50%; font-weight: 900; letter-spacing: 2px; line-height: 1; }
.spark { position: absolute; top: 6px; right: 7px; color: #bfe7cd; font-size: 13px; }
.chat-label { position: absolute; top: calc(100% + 5px); right: -3px; padding: 5px 10px; color: #28312d; background: #fff; border-radius: 999px; box-shadow: 0 5px 14px rgba(0,0,0,.1); font-size: 11px; white-space: nowrap; }
.chat-panel { position: fixed; z-index: 109; right: 30px; bottom: 112px; width: min(390px, calc(100vw - 32px)); height: min(570px, calc(100vh - 150px)); display: grid; grid-template-rows: auto 1fr auto; overflow: hidden; background: #fff; border: 1px solid #dfe9e2; border-radius: 22px; box-shadow: 0 24px 70px rgba(21, 54, 38, .24); }
.chat-header { display: flex; align-items: center; justify-content: space-between; padding: 18px 20px; color: #fff; background: var(--green-900); }
.chat-header div { display: grid; gap: 2px; }
.chat-header strong { font-size: 17px; }
.chat-header small { color: #cde2d5; font-size: 12px; }
.close-button { padding: 2px 7px; color: #fff; background: transparent; border: 0; font-size: 28px; line-height: 1; cursor: pointer; }
.message-list { display: flex; flex-direction: column; gap: 12px; overflow-y: auto; padding: 18px; background: #f5f8f5; }
.message { align-self: flex-start; max-width: 84%; padding: 11px 14px; color: #26322c; background: #fff; border-radius: 5px 16px 16px 16px; box-shadow: 0 3px 12px rgba(35, 55, 44, .06); }
.message.user { align-self: flex-end; color: #fff; background: var(--green-900); border-radius: 16px 5px 16px 16px; }
.message.error { color: #9b302c; background: #fff0ef; }
.message p { margin: 0; white-space: pre-wrap; font-size: 14px; line-height: 1.55; }
.message.loading { color: #66736c; font-size: 13px; }
.references { display: grid; gap: 5px; margin-top: 9px; padding-top: 8px; border-top: 1px solid #e4ebe6; }
.references a { color: var(--green-900); font-size: 12px; font-weight: 700; text-decoration: none; }
.chat-form { display: grid; grid-template-columns: 1fr auto; gap: 8px; padding: 13px; border-top: 1px solid #e1e8e3; background: #fff; }
.chat-form textarea { min-height: 43px; max-height: 100px; resize: none; padding: 11px 12px; border: 1px solid #ccd8d0; border-radius: 12px; font: inherit; line-height: 1.35; }
.chat-form textarea:focus { outline: 2px solid rgba(22, 112, 69, .22); border-color: var(--green-900); }
.chat-form button { align-self: stretch; padding: 0 15px; color: #fff; background: var(--green-900); border: 0; border-radius: 12px; font-weight: 700; cursor: pointer; }
.chat-form button:disabled { opacity: .45; cursor: default; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; }
@media (max-width: 560px) {
  .chat-button { right: 16px; bottom: 18px; width: 60px; height: 60px; }
  .chat-panel { right: 12px; bottom: 92px; width: calc(100vw - 24px); height: min(570px, calc(100vh - 110px)); }
}
</style>
