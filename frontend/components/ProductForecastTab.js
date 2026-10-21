import { useState, useEffect, useRef, useMemo } from "react";
import ProductForecastChart from "./ProductForecastChart";
import {
  getForecastCategories,
  getForecastNextWeek,
  getForecastChart,
  getForecastSummary,
  uploadForecastCsv,
  resetForecast,
} from "../lib/api";

function formatCurrency(val) {
  if (val === undefined || val === null) return "…";
  return "$" + Number(val).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function ProductForecastTab({ initialItem, onForecastUpdated, onOpenApproval }) {
  const [categoriesData, setCategoriesData] = useState(null);
  const [allNextWeek, setAllNextWeek] = useState([]);
  const [summaryData, setSummaryData] = useState(null);

  const [selectedCategory, setSelectedCategory] = useState("");
  const [selectedItem, setSelectedItem] = useState(initialItem || "");
  const [chartData, setChartData] = useState(null);
  const [chartLoading, setChartLoading] = useState(false);
  const [chartError, setChartError] = useState(null);

  // Search state
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(0);

  // CSV upload state
  const [showUpload, setShowUpload] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(null);
  const [uploadError, setUploadError] = useState(null);
  const [generatedAction, setGeneratedAction] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const csvInputRef = useRef(null);

  const searchContainerRef = useRef(null);
  const chartSectionRef = useRef(null);

  async function handleCsvUpload(file) {
    if (!file) return;
    setUploading(true);
    setUploadError(null);
    setUploadSuccess(null);
    setGeneratedAction(null);
    try {
      const res = await uploadForecastCsv(file);
      const addedText = res.new_items_added > 0 ? ` and added ${res.new_items_added} new product(s)` : "";
      setUploadSuccess(`Successfully updated ${res.items_updated} item(s)${addedText} from "${file.name}"!`);
      if (res.action) {
        setGeneratedAction(res.action);
      }
      const [cats, nw, summ] = await Promise.all([
        getForecastCategories(),
        getForecastNextWeek(),
        getForecastSummary(),
      ]);
      setCategoriesData(cats);
      setAllNextWeek(nw.items || []);
      setSummaryData(summ);
      if (selectedItem) {
        getForecastChart(selectedItem).then(setChartData).catch(() => {});
      }
      if (onForecastUpdated) onForecastUpdated();
    } catch (err) {
      setUploadError(err.message || "Failed to process forecast CSV");
    } finally {
      setUploading(false);
    }
  }

  async function handleResetForecast() {
    setUploading(true);
    setUploadError(null);
    setUploadSuccess(null);
    try {
      await resetForecast();
      setUploadSuccess("Forecasts reset to baseline Prophet models.");
      const [cats, nw, summ] = await Promise.all([
        getForecastCategories(),
        getForecastNextWeek(),
        getForecastSummary(),
      ]);
      setCategoriesData(cats);
      setAllNextWeek(nw.items || []);
      setSummaryData(summ);
      if (selectedItem) {
        getForecastChart(selectedItem).then(setChartData).catch(() => {});
      }
      if (onForecastUpdated) onForecastUpdated();
    } catch (err) {
      setUploadError(err.message || "Failed to reset forecast");
    } finally {
      setUploading(false);
    }
  }

  function handleDownloadSample() {
    const csvContent =
      "sub_category,category,price_change_pct,stock,predicted_sales\n" +
      "Accessories,Technology,5,250,1120.00\n" +
      "Chairs,Furniture,-3,180,1650.00\n" +
      "Phones,Technology,10,300,2100.00\n" +
      "Storage,Office Supplies,0,400,950.00\n" +
      "Binders,Office Supplies,2,350,820.00\n" +
      "Paper,Office Supplies,-5,500,740.00\n" +
      "Smartwatches,Technology,0,150,1280.00\n" +
      "Ergonomic Desks,Furniture,0,80,1850.00\n";
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", "forecast_inventory_template.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  // 1. Initial Load: categories, next-week items, and summary
  useEffect(() => {
    let isMounted = true;
    Promise.all([getForecastCategories(), getForecastNextWeek(), getForecastSummary()])
      .then(([cats, nw, summ]) => {
        if (!isMounted) return;
        setCategoriesData(cats);
        setAllNextWeek(nw.items || []);
        setSummaryData(summ);

        // Pick default item if not already set: first item of first group
        const groupNames = Object.keys(cats.groups || {});
        if (groupNames.length > 0) {
          const firstGrp = groupNames[0];
          const firstItems = cats.groups[firstGrp] || [];
          const initialSelection = initialItem || (firstItems.length > 0 ? firstItems[0] : "");
          // Find category for initialSelection
          let foundCategory = firstGrp;
          for (const [grp, items] of Object.entries(cats.groups)) {
            if (items.includes(initialSelection)) {
              foundCategory = grp;
              break;
            }
          }
          setSelectedCategory(foundCategory);
          setSelectedItem(initialSelection);
        }
      })
      .catch((err) => {
        console.error("Failed to load initial forecast data:", err);
      });

    return () => {
      isMounted = false;
    };
  }, [initialItem]);

  // 2. Fetch Chart Data when selectedItem changes
  useEffect(() => {
    if (!selectedItem) return;
    let isMounted = true;
    setChartLoading(true);
    setChartError(null);

    getForecastChart(selectedItem)
      .then((data) => {
        if (!isMounted) return;
        setChartData(data);
        setChartLoading(false);
      })
      .catch((err) => {
        if (!isMounted) return;
        setChartError(err.message || "Failed to load chart");
        setChartLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [selectedItem]);

  // Handle category change from dropdown
  const handleCategoryChange = (newCategory) => {
    setSelectedCategory(newCategory);
    const itemsInCat = categoriesData?.groups[newCategory] || [];
    if (!itemsInCat.includes(selectedItem)) {
      if (itemsInCat.length > 0) {
        setSelectedItem(itemsInCat[0]);
      }
    }
  };

  // Handle item selection from anywhere (search, dropdown, table)
  const handleSelectItem = (item, shouldScroll = false) => {
    if (!item) return;
    setSelectedItem(item);
    setSearchQuery("");
    setIsSearchOpen(false);

    // Sync category dropdown
    if (categoriesData?.groups) {
      for (const [grp, items] of Object.entries(categoriesData.groups)) {
        if (items.includes(item)) {
          setSelectedCategory(grp);
          break;
        }
      }
    }

    if (shouldScroll && chartSectionRef.current) {
      chartSectionRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  // Search suggestions filtered and grouped by category
  const filteredSuggestions = useMemo(() => {
    if (!searchQuery.trim() || !categoriesData?.groups) return [];
    const q = searchQuery.toLowerCase().trim();
    const result = [];

    for (const [category, items] of Object.entries(categoriesData.groups)) {
      const matched = items.filter((it) => it.toLowerCase().includes(q));
      if (matched.length > 0) {
        result.push({ category, items: matched });
      }
    }
    return result;
  }, [searchQuery, categoriesData]);

  // Flattened list for keyboard arrow navigation
  const flatSuggestions = useMemo(() => {
    const list = [];
    filteredSuggestions.forEach((grp) => {
      grp.items.forEach((item) => list.push({ item, category: grp.category }));
    });
    return list;
  }, [filteredSuggestions]);

  // Keyboard navigation for search dropdown
  const handleSearchKeyDown = (e) => {
    if (!isSearchOpen || flatSuggestions.length === 0) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlightedIndex((prev) => (prev + 1) % flatSuggestions.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightedIndex((prev) => (prev - 1 + flatSuggestions.length) % flatSuggestions.length);
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (flatSuggestions[highlightedIndex]) {
        handleSelectItem(flatSuggestions[highlightedIndex].item);
      }
    } else if (e.key === "Escape") {
      setIsSearchOpen(false);
    }
  };

  // Close search suggestions when clicking outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (searchContainerRef.current && !searchContainerRef.current.contains(e.target)) {
        setIsSearchOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Next-week summary values from first point of forecast
  const nextWeekPoint = chartData?.forecast?.[0];
  const itemsInCurrentCategory = categoriesData?.groups[selectedCategory] || [];

  // Grouped table rows
  const groupedTableRows = useMemo(() => {
    if (!categoriesData?.groups || allNextWeek.length === 0) return [];
    const lookup = {};
    allNextWeek.forEach((it) => {
      lookup[it.sub_category] = it;
    });

    const groups = [];
    for (const [grpName, items] of Object.entries(categoriesData.groups)) {
      const rows = items.map((sub) => lookup[sub]).filter(Boolean);
      groups.push({ category: grpName, rows });
    }
    return groups;
  }, [categoriesData, allNextWeek]);

  return (
    <div>
      {/* 1. Topbar with Upload & Custom Status */}
      <div className="topbar">
        <div>
          <h2>Product forecast</h2>
          <div className="sub">
            {summaryData?.meta?.dataset || "Superstore sales, 2015-2018 (demo data)"} ({summaryData?.meta?.currency || "USD"})
          </div>
        </div>
        <div style={{ display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" }}>
          {summaryData?.is_custom && (
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "11px",
                  fontWeight: 700,
                  padding: "3px 8px",
                  borderRadius: "4px",
                  background: "rgba(62,207,142,0.12)",
                  color: "var(--accent)",
                  border: "1px solid rgba(62,207,142,0.3)",
                }}
              >
                ● Custom inventory active
              </span>
              <button
                type="button"
                className="btn ghost"
                onClick={handleResetForecast}
                disabled={uploading}
                style={{ fontSize: "12px", padding: "4px 10px", width: "auto" }}
                title="Revert back to original baseline Prophet forecast"
              >
                Reset to baseline
              </button>
            </div>
          )}

          <button
            type="button"
            className="btn primary"
            onClick={() => setShowUpload(!showUpload)}
            style={{ width: "auto", fontSize: "12.5px", display: "flex", alignItems: "center", gap: "6px" }}
          >
            <span>{showUpload ? "✕ Close Upload" : "📤 Upload updated items (CSV)"}</span>
          </button>

          <span className="pill">
            <span className="dot pulse"></span>Prophet · 80% range
          </span>
        </div>
      </div>

      {/* Upload Drawer / Card */}
      {showUpload && (
        <div
          className="card"
          style={{
            marginBottom: 20,
            background: "var(--panel-2)",
            border: "1px solid var(--accent)",
            animation: "fadeIn 0.2s ease-out",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
            <div>
              <h3 style={{ margin: 0, fontSize: "15px", color: "var(--text)" }}>
                Upload Updated Item List &amp; Price Changes
              </h3>
              <div className="cardsub" style={{ marginBottom: 0, marginTop: 4 }}>
                Update product pricing, stock counts, or add new items. The model will dynamically re-project next-week and 4-week forecasts.
              </div>
            </div>
            <button
              type="button"
              className="btn ghost"
              onClick={handleDownloadSample}
              style={{ fontSize: "12px", padding: "4px 12px", width: "auto", color: "var(--accent)", borderColor: "var(--border)" }}
              title="Download an example CSV template"
            >
              📥 Download Sample CSV
            </button>
          </div>

          <div
            className={`upload-zone ${isDragging ? "dragging" : ""}`}
            style={{
              padding: "24px 20px",
              cursor: uploading ? "wait" : "pointer",
              background: "var(--panel)",
            }}
            onDragOver={(e) => {
              e.preventDefault();
              if (!uploading) setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setIsDragging(false);
              if (uploading) return;
              const file = e.dataTransfer?.files?.[0];
              if (file) handleCsvUpload(file);
            }}
            onClick={() => !uploading && csvInputRef.current?.click()}
          >
            <input
              ref={csvInputRef}
              type="file"
              accept=".csv,text/csv"
              style={{ display: "none" }}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleCsvUpload(file);
                e.target.value = "";
              }}
            />
            <div style={{ fontSize: "28px", marginBottom: "8px" }}>📊</div>
            <div style={{ fontSize: "13.5px", fontWeight: 600, color: "var(--text)", marginBottom: "4px" }}>
              {uploading ? "Processing CSV & re-projecting forecast…" : "Drop updated item CSV here, or click to browse"}
            </div>
            <div style={{ fontSize: "11.5px", color: "var(--faint)" }}>
              Accepts columns: <code>sub_category</code>, <code>category</code>, <code>price_change_pct</code>, <code>stock</code>, <code>predicted_sales</code>
            </div>
          </div>
        </div>
      )}

      {/* Status banners */}
      {uploadSuccess && (
        <div
          className="upload-status success"
          style={{
            marginBottom: 16,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "10px",
            padding: "12px 16px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span>{uploadSuccess}</span>
          </div>
          {generatedAction && (
            <button
              type="button"
              className="btn primary"
              onClick={() => onOpenApproval && onOpenApproval(generatedAction)}
              style={{
                padding: "6px 14px",
                fontSize: "12.5px",
                width: "auto",
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                boxShadow: "0 2px 8px rgba(62,207,142,0.25)",
              }}
            >
              <span>Review &amp; Email Report &rarr;</span>
            </button>
          )}
        </div>
      )}
      {uploadError && (
        <div className="upload-status error" style={{ marginBottom: 16 }}>
          {uploadError}
        </div>
      )}

      {/* 2. Search Bar with Suggestions */}
      <div ref={searchContainerRef} style={{ position: "relative", marginBottom: 18 }}>
        <div style={{ position: "relative" }}>
          <input
            className="field"
            style={{ marginBottom: 0, paddingLeft: 38, fontSize: 13.5 }}
            placeholder="Search product (e.g. Chairs, Phones, Paper)…"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setIsSearchOpen(true);
              setHighlightedIndex(0);
            }}
            onFocus={() => {
              if (searchQuery.trim()) setIsSearchOpen(true);
            }}
            onKeyDown={handleSearchKeyDown}
          />
          <svg
            style={{ position: "absolute", left: 13, top: 13, width: 15, height: 15, color: "var(--muted)" }}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>

        {/* Suggestion Dropdown */}
        {isSearchOpen && filteredSuggestions.length > 0 && (
          <div
            style={{
              position: "absolute",
              top: "calc(100% + 4px)",
              left: 0,
              right: 0,
              background: "var(--panel)",
              border: "1px solid var(--border)",
              borderRadius: 9,
              boxShadow: "0 10px 25px rgba(0,0,0,0.5)",
              zIndex: 50,
              maxHeight: 280,
              overflowY: "auto",
            }}
          >
            {filteredSuggestions.map((group) => (
              <div key={group.category}>
                <div
                  style={{
                    padding: "8px 14px 4px",
                    fontSize: 10.5,
                    fontFamily: "var(--font-mono)",
                    color: "var(--faint)",
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                    borderBottom: "1px solid rgba(42, 50, 66, 0.4)",
                  }}
                >
                  {group.category}
                </div>
                {group.items.map((item) => {
                  const globalIdx = flatSuggestions.findIndex((s) => s.item === item);
                  const isHighlighted = globalIdx === highlightedIndex;
                  return (
                    <div
                      key={item}
                      onClick={() => handleSelectItem(item)}
                      onMouseEnter={() => setHighlightedIndex(globalIdx)}
                      style={{
                        padding: "9px 14px",
                        fontSize: 13,
                        cursor: "pointer",
                        background: isHighlighted ? "var(--panel-2)" : "transparent",
                        color: isHighlighted ? "var(--accent)" : "var(--text)",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                      }}
                    >
                      <span>{item}</span>
                      <span style={{ fontSize: 11, color: "var(--muted)" }}>{group.category}</span>
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 3. Main Row: Two Columns (Chart on Left, Controls & Summary on Right) */}
      <div ref={chartSectionRef} className="grid" style={{ gridTemplateColumns: "1.7fr 1fr", marginBottom: 20 }}>
        {/* Left: Chart Card */}
        <div className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
            <div>
              <h3>{selectedItem || "Product"} — Sales &amp; Forecast</h3>
              <div className="cardsub" style={{ marginBottom: 0 }}>
                {selectedCategory} · 52 weeks history + 4 weeks Prophet forecast
              </div>
            </div>
            <span className="pill" style={{ fontSize: 10.5 }}>
              USD ($)
            </span>
          </div>

          <ProductForecastChart
            chartData={chartData}
            loading={chartLoading}
            error={chartError}
          />
        </div>

        {/* Right: Controls & Next-Week Summary Card */}
        <div className="card" style={{ display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
          <div>
            <h3>Product selection</h3>
            <div className="cardsub">Filter by category and item</div>

            <label className="field-label">Category</label>
            <select
              className="field"
              value={selectedCategory}
              onChange={(e) => handleCategoryChange(e.target.value)}
              style={{ cursor: "pointer" }}
            >
              {categoriesData?.groups &&
                Object.keys(categoriesData.groups).map((grp) => (
                  <option key={grp} value={grp}>
                    {grp}
                  </option>
                ))}
            </select>

            <label className="field-label">Sub-Category</label>
            <select
              className="field"
              value={selectedItem}
              onChange={(e) => handleSelectItem(e.target.value)}
              style={{ cursor: "pointer" }}
            >
              {itemsInCurrentCategory.map((it) => (
                <option key={it} value={it}>
                  {it}
                </option>
              ))}
            </select>
          </div>

          {/* Next-week summary box */}
          <div
            style={{
              background: "var(--panel-2)",
              border: "1px solid var(--border)",
              borderRadius: 11,
              padding: "16px 18px",
              marginTop: 14,
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <span style={{ fontSize: 11.5, color: "var(--muted)", fontWeight: 500 }}>
                Next-week prediction
              </span>
              <span style={{ fontSize: 11, color: "var(--faint)", fontFamily: "var(--font-mono)" }}>
                Ending {nextWeekPoint?.date || "2019-01-06"}
              </span>
            </div>

            <div
              style={{
                fontSize: 26,
                fontWeight: 600,
                color: "var(--accent)",
                fontFamily: "var(--font-mono)",
                letterSpacing: "-0.02em",
                marginBottom: 6,
              }}
            >
              {nextWeekPoint ? formatCurrency(nextWeekPoint.predicted) : "…"}
            </div>

            <div style={{ fontSize: 12, color: "var(--muted)", lineHeight: 1.5 }}>
              80% uncertainty range:{" "}
              <strong style={{ color: "var(--text)", fontFamily: "var(--font-mono)" }}>
                {nextWeekPoint
                  ? `${formatCurrency(nextWeekPoint.lower)} – ${formatCurrency(nextWeekPoint.upper)}`
                  : "…"}
              </strong>
            </div>
          </div>
        </div>
      </div>

      {/* 4. "Next week, all products" Table Grouped by Category */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
          <div>
            <h3>Next week, all products</h3>
            <div className="cardsub" style={{ marginBottom: 0 }}>
              All 17 sub-categories · click a row to view chart
            </div>
          </div>
          <span style={{ fontSize: 11.5, color: "var(--muted)" }}>
            Total forecast: <strong style={{ color: "var(--accent)", fontFamily: "var(--font-mono)" }}>{formatCurrency(summaryData?.next_week_total)}</strong>
          </span>
        </div>

        <div style={{ overflowX: "auto" }}>
          <table>
            <thead>
              <tr>
                <th style={{ width: "35%" }}>Item</th>
                <th style={{ width: "20%", textAlign: "right" }}>Lower est.</th>
                <th style={{ width: "25%", textAlign: "right" }}>Predicted</th>
                <th style={{ width: "20%", textAlign: "right" }}>Upper est.</th>
              </tr>
            </thead>
            <tbody>
              {groupedTableRows.map((group) => (
                <tr key={group.category} style={{ borderBottom: "none" }}>
                  <td colSpan="4" style={{ padding: 0 }}>
                    <div
                      style={{
                        padding: "10px 8px 6px",
                        fontSize: 11,
                        fontWeight: 600,
                        color: "var(--accent)",
                        letterSpacing: "0.04em",
                        textTransform: "uppercase",
                        borderBottom: "1px solid var(--border)",
                        background: "rgba(29, 35, 48, 0.4)",
                      }}
                    >
                      {group.category}
                    </div>
                    <table style={{ margin: 0 }}>
                      <tbody>
                        {group.rows.map((row) => {
                          const isSelected = row.sub_category === selectedItem;
                          return (
                            <tr
                              key={row.sub_category}
                              onClick={() => handleSelectItem(row.sub_category, true)}
                              style={{
                                cursor: "pointer",
                                background: isSelected ? "rgba(62, 207, 142, 0.08)" : "transparent",
                                transition: "background 0.15s ease",
                              }}
                            >
                              <td style={{ width: "35%", fontWeight: isSelected ? 600 : 400, color: isSelected ? "var(--accent)" : "var(--text)" }}>
                                {isSelected && <span style={{ marginRight: 6 }}>●</span>}
                                {row.sub_category}
                              </td>
                              <td className="amt" style={{ width: "20%", textAlign: "right", color: "var(--faint)" }}>
                                {formatCurrency(row.lower_estimate)}
                              </td>
                              <td className="amt" style={{ width: "25%", textAlign: "right", fontWeight: 600, color: isSelected ? "var(--accent)" : "var(--text)" }}>
                                {formatCurrency(row.predicted_sales)}
                              </td>
                              <td className="amt" style={{ width: "20%", textAlign: "right", color: "var(--muted)" }}>
                                {formatCurrency(row.upper_estimate)}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 5. Footer Line with Range Note & Backtest Accuracy */}
      <div
        style={{
          padding: "12px 16px",
          borderRadius: 9,
          background: "var(--panel-2)",
          border: "1px solid var(--border)",
          fontSize: 12,
          color: "var(--muted)",
          display: "flex",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 10,
          alignItems: "center",
        }}
      >
        <div>
          <span>Backtest (last 12 weeks): </span>
          <strong style={{ color: "var(--text)" }}>
            WAPE {summaryData ? Math.round(summaryData.metrics.wape_pct) : 70}%, RMSE{" "}
            {summaryData ? Math.round(summaryData.metrics.rmse).toLocaleString("en-US") : "1,708"}
          </strong>
          <span> (vs {summaryData ? Math.round(summaryData.metrics.baseline_wape_pct) : 97}% / {summaryData ? Math.round(summaryData.metrics.baseline_rmse).toLocaleString("en-US") : "2,387"} for 'next week = last week')</span>
        </div>
        <div style={{ fontSize: 11, color: "var(--faint)" }}>
          {summaryData?.meta?.range_note || "lower/upper estimate = Prophet's default 80% uncertainty interval"}
        </div>
      </div>
    </div>
  );
}
