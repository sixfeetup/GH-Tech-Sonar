import "@testing-library/jest-dom/vitest";

class FixedResizeObserver implements ResizeObserver {
  constructor(private readonly callback: ResizeObserverCallback) {}

  observe(target: Element): void {
    this.callback(
      [
        {
          target,
          contentRect: {
            width: 800,
            height: 600,
          },
        } as ResizeObserverEntry,
      ],
      this,
    );
  }

  disconnect(): void {}

  unobserve(): void {}
}

globalThis.ResizeObserver = FixedResizeObserver;

window.matchMedia = (query: string) => ({
  matches: false,
  media: query,
  onchange: null,
  addEventListener: () => undefined,
  removeEventListener: () => undefined,
  addListener: () => undefined,
  removeListener: () => undefined,
  dispatchEvent: () => false,
});
