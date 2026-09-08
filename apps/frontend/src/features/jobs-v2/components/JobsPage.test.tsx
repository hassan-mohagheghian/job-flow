import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { JobsPage } from "./JobsPage";
import type { CreateEntityFormData } from "@/shared/components/CreateEntityDrawer";

vi.mock("@/shared/components/CreateEntityDrawer", () => ({
  default: ({
    open,
    onSubmit,
    error,
    errorLink,
  }: {
    open: boolean;
    onSubmit: (data: CreateEntityFormData) => void;
    error?: string | null;
    errorLink?: { label: string; href: string } | null;
  }) =>
    open ? (
      <div>
        <button
          onClick={() =>
            onSubmit({
              mode: "job",
              job_post_url: "https://example.com/job",
              links: [],
              notes: [],
              queue: true,
            })
          }
        >
          submit-and-queue
        </button>
        <button
          onClick={() =>
            onSubmit({
              mode: "job",
              job_post_url: "https://example.com/job",
              links: [],
              notes: [],
              queue: false,
            })
          }
        >
          submit-only
        </button>
        {error && <span data-testid="create-error">{error}</span>}
        {errorLink && (
          <a href={errorLink.href} data-testid="create-error-link">
            {errorLink.label}
          </a>
        )}
      </div>
    ) : null,
}));

vi.mock("./JobsHeader", () => ({ JobsHeader: () => null }));
vi.mock("./JobsToolbar", () => ({ JobsToolbar: () => null }));
vi.mock("./JobsTable", () => ({ JobsTable: () => null }));
vi.mock("./ProcessingDrawer", () => ({ ProcessingDrawer: () => null }));
vi.mock("./JobDetailDrawer", () => ({ JobDetailDrawer: () => null }));
vi.mock("./JobEditDrawer", () => ({ JobEditDrawer: () => null }));

function renderPage(overrides: Record<string, unknown> = {}) {
  const props = {
    items: [],
    total: 0,
    loadedCount: 0,
    isLoading: false,
    isFetchingNextPage: false,
    hasNextPage: false,
    onFetchNextPage: vi.fn(),
    isError: false,
    error: null,
    onRefetch: vi.fn(),
    query: "",
    onQueryChange: vi.fn(),
    sort: "created_at",
    onSortChange: vi.fn(),
    order: "desc" as const,
    filterProcessingStatus: "",
    onFilterProcessingStatusChange: vi.fn(),
    filterLocation: "",
    onFilterLocationChange: vi.fn(),
    filterRemote: "",
    onFilterRemoteChange: vi.fn(),
    filterVisa: "",
    onFilterVisaChange: vi.fn(),
    filterPinned: false,
    onFilterPinnedChange: vi.fn(),
    activeFilterCount: 0,
    onClearFilters: vi.fn(),
    onProcessV2: vi.fn(),
    onReprocess: vi.fn(),
    onViewDetails: vi.fn(),
    onEdit: vi.fn(),
    onDelete: vi.fn(),
    onTogglePinned: vi.fn(),
    isProcessing: false,
    queueDrawerOpen: false,
    onQueueDrawerOpenChange: vi.fn(),
    queueReloadKey: 0,
    addJobDrawerOpen: true,
    onAddJobDrawerOpenChange: vi.fn(),
    onJobQueued: vi.fn(),
    detailJobId: null,
    onDetailJobIdChange: vi.fn(),
    editJobId: null,
    onEditJobIdChange: vi.fn(),
    processingCount: 0,
    ...overrides,
  };
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <JobsPage {...(props as any)} />
    </QueryClientProvider>,
  );
}

describe("JobsPage create & queue flow", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              id: "job-1",
              status: "queued",
              execution_id: "exec-1",
            }),
        }),
      ),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("opens the processing drawer and bumps the queue reload key when queue is requested", async () => {
    const onQueueDrawerOpenChange = vi.fn();
    const onJobQueued = vi.fn();
    const onAddJobDrawerOpenChange = vi.fn();
    const onRefetch = vi.fn();

    renderPage({
      onQueueDrawerOpenChange,
      onJobQueued,
      onAddJobDrawerOpenChange,
      onRefetch,
    });

    fireEvent.click(screen.getByText("submit-and-queue"));

    await waitFor(() => {
      expect(onAddJobDrawerOpenChange).toHaveBeenCalledWith(false);
      expect(onJobQueued).toHaveBeenCalledTimes(1);
      expect(onQueueDrawerOpenChange).toHaveBeenCalledWith(true);
      expect(onRefetch).toHaveBeenCalledTimes(1);
    });
  });

  it("does not touch the queue drawer when the job is created without queueing", async () => {
    const onQueueDrawerOpenChange = vi.fn();
    const onJobQueued = vi.fn();
    const onAddJobDrawerOpenChange = vi.fn();
    const onRefetch = vi.fn();

    renderPage({
      onQueueDrawerOpenChange,
      onJobQueued,
      onAddJobDrawerOpenChange,
      onRefetch,
    });

    fireEvent.click(screen.getByText("submit-only"));

    await waitFor(() => {
      expect(onAddJobDrawerOpenChange).toHaveBeenCalledWith(false);
      expect(onRefetch).toHaveBeenCalledTimes(1);
    });
    expect(onJobQueued).not.toHaveBeenCalled();
    expect(onQueueDrawerOpenChange).not.toHaveBeenCalled();
  });

  it("links the duplicate-job error to the existing job application page", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: false,
          status: 409,
          json: () =>
            Promise.resolve({
              error: {
                message: "A Job with the same primary URL already exists.",
                details: { job_id: "job-1" },
              },
            }),
        }),
      ),
    );
    renderPage();

    fireEvent.click(screen.getByText("submit-only"));

    await waitFor(() => {
      const link = screen.getByTestId("create-error-link");
      expect(link).toHaveAttribute("href", "/jobs/job-1/application");
      expect(link.textContent).toBe("Open application");
    });
    expect(screen.getByTestId("create-error").textContent).toBe(
      "A Job with the same primary URL already exists.",
    );
  });
});
