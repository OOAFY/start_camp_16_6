import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  headers: {
    'Content-Type': 'application/json'
  }
})

api.interceptors.response.use(
  response => response,
  error => {
    return Promise.reject(error.response?.data || error)
  }
)

export function fetchPlaces(params = {}) {
  return api.get('/places', { params }).then(res => res.data.data)
}

export function fetchPlaceDetail(contentId) {
  return api.get(`/places/${contentId}`).then(res => res.data.data)
}

export function fetchFestivals(params = {}) {
  return api.get('/festivals', { params }).then(res => res.data.data)
}

export function fetchFestivalDetail(contentId) {
  // FullCalendar의 eventClick에서 info.event.id를 넘기면 상세 팝업에 사용할 수 있습니다.
  // 정제된 30개 축제 날짜는 모두 확정 일정으로 표시합니다.
  return api.get(`/festivals/${contentId}`).then(res => res.data.data)
}

export function fetchPosts(params = {}) {
  return api.get('/posts', { params }).then(res => res.data.data)
}

export function fetchPostDetail(postId) {
  return api.get(`/posts/${postId}`).then(res => res.data.data)
}

export function createPost(payload) {
  return api.post('/posts', payload).then(res => res.data.data)
}

export function updatePost(postId, payload) {
  return api.put(`/posts/${postId}`, payload).then(res => res.data.data)
}

export function deletePost(postId, password) {
  return api.delete(`/posts/${postId}`, { data: { password } }).then(res => res.data.data)
}

export function sendChat(message, history = []) {
  return api.post('/chat', { message, history }).then(res => res.data.data)
}

export default api
