import '@testing-library/jest-dom/vitest'

if (typeof globalThis.createImageBitmap !== 'function') {
  globalThis.createImageBitmap = async (_blob: Blob) =>
    ({ width: 1, height: 1, close: () => {} }) as ImageBitmap
}

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
})

