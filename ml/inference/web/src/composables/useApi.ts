import axios, { AxiosError } from 'axios'

const client = axios.create({
  baseURL: '',
  headers: {
    'Content-Type': 'application/json'
  }
})

export function useApi() {
  async function get<T>(url: string): Promise<T> {
    try {
      const response = await client.get<T>(url)
      return response.data
    } catch (error) {
      throw handleError(error)
    }
  }

  async function post<T>(url: string, data?: unknown): Promise<T> {
    try {
      const response = await client.post<T>(url, data)
      return response.data
    } catch (error) {
      throw handleError(error)
    }
  }

  async function put<T>(url: string, data?: unknown): Promise<T> {
    try {
      const response = await client.put<T>(url, data)
      return response.data
    } catch (error) {
      throw handleError(error)
    }
  }

  async function patch<T>(url: string, data?: unknown): Promise<T> {
    try {
      const response = await client.patch<T>(url, data)
      return response.data
    } catch (error) {
      throw handleError(error)
    }
  }

  async function del<T>(url: string): Promise<T> {
    try {
      const response = await client.delete<T>(url)
      return response.data
    } catch (error) {
      throw handleError(error)
    }
  }

  function handleError(error: unknown): Error {
    if (error instanceof AxiosError) {
      const message = error.response?.data?.detail || error.message
      return new Error(message)
    }
    return error instanceof Error ? error : new Error('An unknown error occurred')
  }

  return {
    get,
    post,
    put,
    patch,
    delete: del
  }
}
