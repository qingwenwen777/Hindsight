import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 py-24">
      <h1 className="text-display text-primary">404</h1>
      <p className="text-small text-secondary">页面不存在。</p>
      <Link
        href="/"
        className="rounded-md bg-btn-primary px-4 py-2 text-small font-medium text-btn-primary-fg transition-opacity hover:opacity-90"
      >
        回到仪表盘
      </Link>
    </div>
  );
}
