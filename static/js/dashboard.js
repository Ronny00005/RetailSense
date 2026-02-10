
let charts = {};


document.addEventListener('DOMContentLoaded', () => {
    
    if (typeof categoryChartData !== 'undefined') {
        initializeCategoryCharts();
    }
    if (typeof forecastChartData !== 'undefined') {
        initializeForecastChart();
    }
});

function showSection(sectionId) {
    
    document.querySelectorAll(".content-section").forEach(sec => {
        sec.classList.remove("active");
    });

   
    document.getElementById(sectionId).classList.add("active");

    
    document.querySelectorAll(".nav-item").forEach(btn => {
        btn.classList.remove("active");
    });

    
    document
        .querySelector(`.nav-item[onclick="showSection('${sectionId}')"]`)
        .classList.add("active");

    
    
     if (sectionId === "inventory") {
        setTimeout(() => {
            loadInventory();
        }, 200);
    }


if (sectionId === "category") {
    loadCategoryCharts();
    loadCategoryDropdown();
}
if (sectionId === "product-intelligence") {
    loadProductIntelligence();
}

}

function uploadCSV(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);

    fetch("/upload", {
        method: "POST",
        body: formData
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            window.location.href = data.redirect;
        } else {
            alert(data.message || "Upload failed");
        }
    })
    .catch(() => {
        alert("Upload error");
    });
}



function changePassword(event) {
    event.preventDefault();

    const currentPassword = document.getElementById("currentPassword").value;
    const newPassword = document.getElementById("newPassword").value;
    const confirmPassword = document.getElementById("confirmPassword").value;

    if (newPassword !== confirmPassword) {
        alert("New passwords do not match");
        return;
    }

    fetch("/api/change-password", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            current_password: currentPassword,
            new_password: newPassword
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            alert("Password changed successfully");

            
            document.getElementById("currentPassword").value = "";
            document.getElementById("newPassword").value = "";
            document.getElementById("confirmPassword").value = "";
        } else {
            alert(data.message || "Password change failed");
        }
    })
    .catch(() => {
        alert("Server error. Try again later.");
    });
}


function logout() {
    if (confirm('Are you sure you want to logout?')) {
        window.location.href = '/logout';
    }
}


function toggleSidebar() {
    document.querySelector('.sidebar').classList.toggle('active');
}


if (window.innerWidth <= 1024) {
    window.addEventListener('DOMContentLoaded', () => {
        const header = document.querySelector('.content-header');
        const menuBtn = document.createElement('button');
        menuBtn.innerHTML = '☰';
        menuBtn.className = 'mobile-menu-btn';
        menuBtn.style.cssText = 'background: transparent; border: none; font-size: 1.5rem; cursor: pointer; margin-right: 1rem;';
        menuBtn.onclick = toggleSidebar;
        header.insertBefore(menuBtn, header.firstChild);
    });
}
function generateReport(event) {
    event.preventDefault();

    const fromDate = document.getElementById("dateFrom").value;
    const toDate = document.getElementById("dateTo").value;

    fetch("/api/datewise-report", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            from_date: fromDate,
            to_date: toDate
        })
    })
    .then(res => res.json())
    .then(data => {
        if (!data.success) return;

        document.getElementById("reportSales").innerText = data.sales;
        document.getElementById("reportProfit").innerText = data.profit;
        document.getElementById("reportTopProduct").innerText = data.top_product;
        document.getElementById("reportWorstProduct").innerText = data.worst_product;

        document.getElementById("reportResults").classList.remove("hidden");
    });
}
function downloadExcel() {
    const fromDate = document.getElementById("dateFrom").value;
    const toDate = document.getElementById("dateTo").value;

    fetch("/download/excel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ from_date: fromDate, to_date: toDate })
    })
    .then(res => res.blob())
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "datewise_report.xlsx";
        a.click();
    });
}
let categoryBarChart = null;
let categoryPieChart = null;

function loadCategoryCharts() {
    fetch("/api/category-charts")
        .then(res => res.json())
        .then(data => {
            if (!data.success) return;

            const labels = data.labels;
            const values = data.values;

            renderCategoryBarChart(labels, values);
            renderCategoryPieChart(labels, values);
        });
}

function renderCategoryBarChart(labels, values) {
    const ctx = document.getElementById("categoryBarChart").getContext("2d");

    if (categoryBarChart) {
        categoryBarChart.destroy();
    }

    categoryBarChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [{
                label: "Sales by Category",
                data: values,
                borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

function renderCategoryPieChart(labels, values) {
    const ctx = document.getElementById("categoryPieChart").getContext("2d");

    if (categoryPieChart) {
        categoryPieChart.destroy();
    }

    categoryPieChart = new Chart(ctx, {
        type: "pie",
        data: {
            labels: labels,
            datasets: [{
                data: values
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: "bottom"
                }
            }
        }
    });
}

window.addEventListener('resize', () => {
    if (window.innerWidth > 1024) {
        document.querySelector('.sidebar').classList.remove('active');
    }
});

document.addEventListener("DOMContentLoaded", () => {
    fetch("/api/monthly-sales")
        .then(res => res.json())
        .then(data => {
            if (!data.success) return;

            const ctx = document.getElementById("monthlySalesChart");

            const chart = new Chart(ctx, {
                type: "bar",
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: "Monthly Sales",
                        data: data.values,
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });

    
            setTimeout(() => chart.resize(), 100);
        });
});

let inventoryChart = null;

function loadInventory() {
    fetch("/api/inventory")
        .then(res => res.json())
        .then(data => {
            if (!data.success) return;

            document.getElementById("invForecast").innerText =
                data.forecast.toLocaleString();

            document.getElementById("invStock").innerText =
                data.current_stock.toLocaleString();

            document.getElementById("invAction").innerText =
                data.action;

            renderInventoryChart(data);
        });
}

function renderInventoryChart(data) {
    const ctx = document.getElementById("inventoryChart");

    if (inventoryChart) inventoryChart.destroy();

    inventoryChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: ["Forecast Demand", "Current Stock"],
            datasets: [{
                data: [data.forecast, data.current_stock],
                borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true }
            }
        }
    });
}
function loadCategoryDropdown() {
    fetch("/api/categories")
        .then(res => res.json())
        .then(data => {
            if (!data.success) return;

            const select = document.getElementById("categorySelect");
            select.innerHTML = `<option value="">-- Select Category --</option>`;

            data.categories.forEach(cat => {
                const opt = document.createElement("option");
                opt.value = cat;
                opt.textContent = cat;
                select.appendChild(opt);
            });
        });
}
function fetchCategorySummary() {
    const category = document.getElementById("categorySelect").value;
    if (!category) return;

    fetch("/api/category-summary", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ category })
    })
    .then(res => res.json())
    .then(data => {
        if (!data.success) return;

        document.getElementById("catSales").innerText =
            "₹ " + data.total_sales.toLocaleString();

        document.getElementById("catProfit").innerText =
            "₹ " + data.total_profit.toLocaleString();

        document.getElementById("catBest").innerText = data.best_item;
        document.getElementById("catWorst").innerText = data.worst_item;

        document.getElementById("categorySummary").style.display = "grid";
    });
}
function loadProductIntelligence() {
    fetch("/api/product-intelligence")
        .then(res => res.json())
        .then(data => {
            if (!data.success) return;

            updateKPIs(data.products);
            renderABCChart(data.products);
            renderProfitVolumeChart(data.products);
            renderProductTable(data.products);
        });
}
function updateKPIs(products) {
    const counts = {};

    products.forEach(p => {
        counts[p.abc_class] = (counts[p.abc_class] || 0) + 1;
    });

    document.getElementById("kpiA").textContent = counts["A"] || 0;
    document.getElementById("kpiB").textContent = counts["B"] || 0;
    document.getElementById("kpiC").textContent = counts["C"] || 0;
}
function renderABCChart(products) {
    const classCounts = {};

    products.forEach(p => {
        classCounts[p.abc_class] = (classCounts[p.abc_class] || 0) + 1;
    });

    new Chart(document.getElementById("abcChart"), {
        type: "bar",
        data: {
            labels: Object.keys(classCounts),
            datasets: [{
                data: Object.values(classCounts)
            }]
        }
    });
}
function renderProfitVolumeChart(products) {
    const grouped = {};

    products.forEach(p => {
        if (!grouped[p.quadrant]) grouped[p.quadrant] = [];
        grouped[p.quadrant].push({
            x: p.quantity,
            y: p.profit,
            label: p.item_name   
        });
    });

    new Chart(document.getElementById("profitVolumeChart"), {
        type: "scatter",
        data: {
            datasets: Object.keys(grouped).map(q => ({
                label: q,
                data: grouped[q]
            }))
        },
        options: {
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(ctx) {
                            const p = ctx.raw;
                            return `${p.label} | Qty: ${p.x}, Profit: ${p.y.toLocaleString()}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: { display: true, text: "Quantity Sold" }
                },
                y: {
                    title: { display: true, text: "Total Profit" }
                }
            }
        }
    });
}

function renderProductTable(products) {
    const tbody = document.getElementById("productTable");
    tbody.innerHTML = "";

    products.forEach(p => {
        const badgeClass =
            p.abc_class === "A" ? "badge-a" :
            p.abc_class === "B" ? "badge-b" : "badge-c";

        tbody.innerHTML += `
            <tr>
                <td><strong>${p.item_name}</strong></td>
                <td>${Number(p.revenue).toLocaleString()}</td>
                <td>${p.quantity}</td>
                <td>${Number(p.profit).toLocaleString()}</td>
                <td><span class="badge ${badgeClass}">${p.abc_class}</span></td>
                <td>${p.quadrant}</td>
            </tr>
        `;
    });
}
