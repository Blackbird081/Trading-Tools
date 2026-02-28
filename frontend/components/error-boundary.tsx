"use client";

/**
 * Error Boundary for trading pages.
 *
 * ★ FIX-04: Prevents unhandled errors from crashing the entire app.
 * ★ Shows user-friendly error message with retry option.
 * ★ Logs errors to console for debugging.
 */

import { Component, type ReactNode, type ErrorInfo } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class TradingErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error("[TradingErrorBoundary] Uncaught error:", error, errorInfo);
    this.props.onError?.(error, errorInfo);
  }

  handleRetry = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex min-h-[200px] flex-col items-center justify-center rounded-lg border border-red-800 bg-red-950/20 p-8 text-center">
          <div className="mb-4 text-4xl">⚠️</div>
          <h3 className="mb-2 text-lg font-semibold text-red-400">
            Đã xảy ra lỗi
          </h3>
          <p className="mb-4 max-w-md text-sm text-zinc-400">
            {this.state.error?.message ?? "Lỗi không xác định. Vui lòng thử lại."}
          </p>
          <button
            onClick={this.handleRetry}
            className="rounded bg-red-700 px-4 py-2 text-sm font-medium text-white hover:bg-red-600"
          >
            Thử lại
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * Lightweight functional wrapper for common use cases.
 */
export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  fallback?: ReactNode,
): React.ComponentType<P> {
  const WrappedComponent = (props: P) => (
    <TradingErrorBoundary fallback={fallback}>
      <Component {...props} />
    </TradingErrorBoundary>
  );
  WrappedComponent.displayName = `withErrorBoundary(${Component.displayName ?? Component.name})`;
  return WrappedComponent;
}
