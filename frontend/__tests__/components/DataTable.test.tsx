import { describe, it, expect, vi } from "vitest";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { DataTable, VirtualDataTable, ColumnDef } from "@/components/ui/DataTable";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string, params?: Record<string, unknown>) => {
    if (params?.page) return `Page ${params.page}`;
    return key;
  },
}));

interface TestItem {
  id: string;
  title: string;
  status: string;
}

const testColumns: ColumnDef<TestItem>[] = [
  {
    key: "id",
    header: "ID",
    cell: (row) => row.id,
    width: "100px",
  },
  {
    key: "title",
    header: "Title",
    cell: (row) => row.title,
  },
  {
    key: "status",
    header: "Status",
    cell: (row) => row.status,
  },
];

const mockData: TestItem[] = [
  { id: "1", title: "Security Alert Alpha", status: "open" },
  { id: "2", title: "Security Alert Beta", status: "investigating" },
  { id: "3", title: "Security Alert Gamma", status: "closed" },
];

describe("DataTable Component", () => {
  it("renders table headers and rows correctly in standard mode", () => {
    const html = renderToStaticMarkup(
      <DataTable data={mockData} columns={testColumns} rowKey={(row) => row.id} />
    );

    expect(html).toContain("ID");
    expect(html).toContain("Title");
    expect(html).toContain("Status");
    expect(html).toContain("Security Alert Alpha");
    expect(html).toContain("Security Alert Beta");
    expect(html).toContain("Security Alert Gamma");
    expect(html).toContain("<table");
  });

  it("renders empty state when data is empty", () => {
    const html = renderToStaticMarkup(
      <DataTable
        data={[]}
        columns={testColumns}
        emptyState={{
          title: "No alerts found",
          description: "Try adjusting your search criteria",
        }}
      />
    );

    expect(html).toContain("No alerts found");
    expect(html).toContain("Try adjusting your search criteria");
    expect(html).not.toContain("<table");
  });

  it("renders pagination controls when total exceeds pageSize", () => {
    const html = renderToStaticMarkup(
      <DataTable data={mockData} columns={testColumns} currentPage={1} pageSize={1} total={3} />
    );

    expect(html).toContain("nextPage");
    expect(html).toContain("prevPage");
    expect(html).toContain("Page 1");
  });

  it("renders virtualized table container and headers correctly", () => {
    const html = renderToStaticMarkup(
      <DataTable
        data={mockData}
        columns={testColumns}
        virtualized={true}
        virtualHeight={300}
        rowHeight={50}
        rowKey={(row) => row.id}
      />
    );

    expect(html).toContain('role="table"');
    expect(html).toContain('role="columnheader"');
    expect(html).toContain("ID");
    expect(html).toContain("Title");
    expect(html).toContain("Status");
    expect(html).toContain("Security Alert Alpha");
  });

  it("renders correctly via VirtualDataTable component alias", () => {
    const html = renderToStaticMarkup(
      <VirtualDataTable
        data={mockData}
        columns={testColumns}
        virtualHeight={400}
        rowHeight={52}
        rowKey={(row) => row.id}
      />
    );

    expect(html).toContain('role="table"');
    expect(html).toContain("Security Alert Alpha");
    expect(html).toContain("Security Alert Beta");
    expect(html).toContain("Security Alert Gamma");
  });
});
