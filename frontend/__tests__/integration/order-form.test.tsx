import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { OrderForm } from "@/app/orders/_components/order-form";
import { useOrderStore } from "@/stores/order-store";
import { useUIStore } from "@/stores/ui-store";

describe("OrderForm integration", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();

    useUIStore.setState({
      activeSymbol: "FPT",
      commandPaletteOpen: false,
      sidebarCollapsed: false,
      preset: "VN30",
      years: 3,
      symbolPopupOpen: false,
      symbolPopupSymbol: null,
    });
  });

  it("blocks non-lot-size quantity and keeps submit disabled", () => {
    render(<OrderForm />);

    fireEvent.change(screen.getByPlaceholderText("100"), { target: { value: "150" } });
    expect(screen.getByText(/bội số của 100/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /mua fpt/i })).toBeDisabled();
  });

  it("supports live two-step confirmation token flow", async () => {
    const placeOrderMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: false,
        message: "Live order cần xác nhận lần 2. Bấm Submit lại để xác nhận.",
        confirmToken: "confirm-123",
      })
      .mockResolvedValueOnce({
        ok: true,
        message: "Order placed",
      });

    useOrderStore.setState({ placeOrder: placeOrderMock } as Partial<ReturnType<typeof useOrderStore.getState>>);

    render(<OrderForm />);

    fireEvent.change(screen.getByPlaceholderText("100"), { target: { value: "200" } });
    fireEvent.change(screen.getByPlaceholderText("0.00"), { target: { value: "25.5" } });
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "live" } });

    fireEvent.click(screen.getByRole("button", { name: /mua fpt/i }));

    await waitFor(() => expect(placeOrderMock).toHaveBeenCalledTimes(1));
    expect(placeOrderMock.mock.calls[0]?.[0]).toMatchObject({
      symbol: "FPT",
      side: "BUY",
      quantity: 200,
      price: 25.5,
      mode: "live",
      confirmToken: undefined,
    });
    expect(screen.getByText(/xác nhận lần 2/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /mua fpt/i }));

    await waitFor(() => expect(placeOrderMock).toHaveBeenCalledTimes(2));
    expect(placeOrderMock.mock.calls[1]?.[0]).toMatchObject({
      mode: "live",
      confirmToken: "confirm-123",
    });

    await waitFor(() => expect(screen.getByText("Đặt lệnh thành công.")).toBeInTheDocument());
    expect(screen.getByPlaceholderText("100")).toHaveValue(null);
    expect(screen.getByPlaceholderText("0.00")).toHaveValue(null);
  });
});

