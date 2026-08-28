// Auth endpoint. Live: POST /auth/login -> { access_token, role }.
import { api, USE_MOCKS, delay } from './client'
import { mockLogin } from './mocks'

export async function login(username, password) {
  if (USE_MOCKS) {
    await delay(250)
    const result = mockLogin(username, password)
    if (!result) {
      const err = new Error('Invalid username or password')
      err.status = 401
      throw err
    }
    return result
  }
  const { data } = await api.post('/auth/login', { username, password })
  return data // { access_token, role }
}
