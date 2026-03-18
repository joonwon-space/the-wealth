/**
 * Dynamic imports for heavy chart libraries (lightweight-charts, Recharts).
 * Using next/dynamic with ssr: false ensures chart code is only loaded in the browser
 * and is split into a separate chunk, reducing initial bundle size.
 */
import dynamic from "next/dynamic";

export const CandlestickChart = dynamic(
  () =>
    import("./CandlestickChart").then((m) => ({ default: m.CandlestickChart })),
  {
    ssr: false,
    loading: () => (
      <div className="h-[300px] animate-pulse rounded-lg bg-muted" />
    ),
  }
);

export const AllocationDonut = dynamic(
  () =>
    import("./AllocationDonut").then((m) => ({ default: m.AllocationDonut })),
  {
    ssr: false,
    loading: () => (
      <div className="h-[240px] animate-pulse rounded-full bg-muted" />
    ),
  }
);

export const SectorAllocationChart = dynamic(
  () =>
    import("./SectorAllocationChart").then((m) => ({
      default: m.SectorAllocationChart,
    })),
  {
    ssr: false,
    loading: () => (
      <div className="h-[240px] animate-pulse rounded-lg bg-muted" />
    ),
  }
);

export const TransactionChart = dynamic(
  () =>
    import("./TransactionChart").then((m) => ({
      default: m.TransactionChart,
    })),
  {
    ssr: false,
    loading: () => (
      <div className="h-[200px] animate-pulse rounded-lg bg-muted" />
    ),
  }
);

export const PortfolioHistoryChart = dynamic(
  () =>
    import("./PortfolioHistoryChart").then((m) => ({
      default: m.PortfolioHistoryChart,
    })),
  {
    ssr: false,
    loading: () => (
      <div className="h-[200px] animate-pulse rounded-lg bg-muted" />
    ),
  }
);
