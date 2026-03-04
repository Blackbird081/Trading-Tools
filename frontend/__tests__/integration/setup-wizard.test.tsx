import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { SetupWizard } from "@/app/settings/_components/setup-wizard";

function jsonResponse(payload: unknown): Response {
  return {
    ok: true,
    json: async () => payload,
  } as Response;
}

describe("SetupWizard (E1 UX-01)", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("tracks unsaved changes and saves draft explicitly", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(jsonResponse({ active_profile: null, profiles: [] }));
    vi.stubGlobal("fetch", fetchMock);

    render(<SetupWizard />);

    expect(await screen.findByText("Saved")).toBeInTheDocument();
    fireEvent.change(screen.getByDisplayValue("data/trading.duckdb"), {
      target: { value: "data/new-trading.duckdb" },
    });

    expect(screen.getByText("Unsaved changes")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /save draft/i }));

    await waitFor(() => expect(screen.getByText("Saved")).toBeInTheDocument());
    expect(localStorage.getItem("tt.local.setup.draft.v1")).toContain(
      "data/new-trading.duckdb",
    );
  });

  it("applies draft by saving and running validation", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ active_profile: null, profiles: [] }))
      .mockResolvedValueOnce(
        jsonResponse({
          matrix: [],
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          valid: true,
          checks: [{ name: "Draft", status: "ok", detail: "ok" }],
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(<SetupWizard />);
    fireEvent.change(await screen.findByDisplayValue("data/trading.duckdb"), {
      target: { value: "data/applied-trading.duckdb" },
    });
    fireEvent.click(screen.getByRole("button", { name: /apply draft/i }));

    await waitFor(() => {
      const calledValidate = fetchMock.mock.calls.some((call) =>
        String(call?.[0] ?? "").includes("/setup/validate"),
      );
      expect(calledValidate).toBe(true);
    });
    expect(await screen.findByText("Draft applied and validation passed.")).toBeInTheDocument();
    expect(localStorage.getItem("tt.local.setup.draft.v1")).toContain(
      "data/applied-trading.duckdb",
    );
  });
});
