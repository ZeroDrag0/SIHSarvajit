import { useSyncExternalStore } from 'react'

export const ROUTES = ['overview', 'viewer', 'units', 'validation', 'data', 'technology'] as const
export type Route = (typeof ROUTES)[number]

export const ROUTE_LABEL: Record<Route, string> = {
  overview: 'Home',
  viewer: 'Explore',
  units: 'Properties',
  validation: 'Validation',
  data: 'Data',
  technology: 'Technology',
}

function parse(hash: string): Route {
  const name = hash.replace(/^#\/?/, '').split(/[/?]/)[0]
  return (ROUTES as readonly string[]).includes(name) ? (name as Route) : 'overview'
}
function subscribe(callback: () => void): () => void {
  window.addEventListener('hashchange', callback)
  return () => window.removeEventListener('hashchange', callback)
}
export function useRoute(): Route {
  return useSyncExternalStore(subscribe, () => parse(window.location.hash), () => 'overview' as Route)
}
export function navigate(route: Route): void {
  const target = `#/${route}`
  if (window.location.hash !== target) window.location.hash = target
}
export function routeHref(route: Route): string { return `#/${route}` }
