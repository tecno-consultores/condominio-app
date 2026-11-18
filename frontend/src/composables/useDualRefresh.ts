import { onBeforeUnmount, onMounted, ref } from 'vue';

export const DEFAULT_POLL_INTERVAL_MS = 30_000;

export function useDualRefresh(
  fetcher: () => Promise<unknown>,
  intervalMs = DEFAULT_POLL_INTERVAL_MS,
) {
  const isRefreshing = ref(false);
  let timerId: ReturnType<typeof setInterval> | null = null;

  async function triggerRefresh(): Promise<void> {
    if (isRefreshing.value) {
      return;
    }
    isRefreshing.value = true;
    try {
      await fetcher();
    } finally {
      isRefreshing.value = false;
    }
  }

  function stopPolling(): void {
    if (timerId !== null) {
      clearInterval(timerId);
      timerId = null;
    }
  }

  function startPolling(): void {
    stopPolling();
    timerId = setInterval(() => {
      if (typeof document !== 'undefined' && document.visibilityState === 'hidden') {
        return;
      }
      void triggerRefresh();
    }, intervalMs);
  }

  onMounted(() => {
    startPolling();
  });

  onBeforeUnmount(() => {
    stopPolling();
  });

  return {
    isRefreshing,
    triggerRefresh,
    startPolling,
    stopPolling,
  };
}
