import { useEffect, useState } from "react";

export const PAGE_SIZE = 10;

export type Pagination<T> = {
  visible: T[];
  page: number;
  pageCount: number;
  total: number;
  pageSize: number;
  setPage: (page: number) => void;
};

export function usePagination<T>(items: T[], pageSize = PAGE_SIZE, resetKey: unknown = null): Pagination<T> {
  const [requested, setPage] = useState(1);
  useEffect(() => { setPage(1); }, [resetKey]);
  const pageCount = Math.max(1, Math.ceil(items.length / pageSize));
  const page = Math.min(Math.max(requested, 1), pageCount);
  return { visible: items.slice((page - 1) * pageSize, page * pageSize), page, pageCount, total: items.length, pageSize, setPage };
}

export function Pager<T>({ pagination, label }: { pagination: Pagination<T>; label: string }) {
  const { page, pageCount, total, pageSize, setPage } = pagination;
  if (total <= pageSize) return null;
  const first = (page - 1) * pageSize + 1;
  const last = Math.min(page * pageSize, total);
  return (
    <nav className="pager" aria-label={`Paginação: ${label}`}>
      <button type="button" onClick={() => setPage(page - 1)} disabled={page <= 1}>Anterior</button>
      <span role="status">Página {page} de {pageCount} · {first}–{last} de {total}</span>
      <button type="button" onClick={() => setPage(page + 1)} disabled={page >= pageCount}>Próxima</button>
    </nav>
  );
}
