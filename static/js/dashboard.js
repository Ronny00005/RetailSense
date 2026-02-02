// ============================================
// RETAIL SENSE - FLASK DASHBOARD JAVASCRIPT
// ============================================

let charts = {};

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    // Initialize charts if data is available
    if (typeof categoryChartData !== 'undefined') {
        initializeCategoryCharts();
    }
    if (typeof forecastChartData !== 'undefined') {
        initializeForecastChart();
    }
});

// ============================================
// NAVIGATION
// ============================================

// function showSection(sectionId) {
//     // Hide all sections
//     document.querySelectorAll('.content-section').forEach(section => {
//         section.classList.remove('active');
//     });
    
//     // Show selected section
//     const targetSection = document.getElementById(sectionId);
//     if (targetSection) {
//         targetSection.classList.add('active');
//     }
    
//     // Update active nav item
//     document.querySelectorAll('.nav-item').forEach(item => {
//         item.classList.remove('active');
//     });
    
//     event.target.closest('.nav-item')?.classList.add('active');
    
//     // Update page title
//     const titles = {
//         'overview': 'Overall View',
//         'category': 'Category Analysis',
//         'future': 'Future Analytics',
//         'datewise': 'Date-wise Report',
//         'profile': 'Profile'
//     };
    
//     document.querySelector('.page-title').textContent = titles[sectionId] || 'Dashboard';
// }
function showSection(sectionId) {
    // Hide all sections
    document.querySelectorAll(".content-section").forEach(sec => {
        sec.classList.remove("active");
    });

    // Show selected section
    document.getElementById(sectionId).classList.add("active");

    // Remove active state from all nav buttons
    document.querySelectorAll(".nav-item").forEach(btn => {
        btn.classList.remove("active");
    });

    // Add active class to clicked nav button
    document
        .querySelector(`.nav-item[onclick="showSection('${sectionId}')"]`)
        .classList.add("active");

    // Load charts only when needed
    if (sectionId === "category") {
        loadCategoryCharts();
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


// ============================================
// CATEGORY ANALYSIS CHARTS
// ============================================

function initializeCategoryCharts() {
    createCategoryBarChart();
    createCategoryPieChart();
}

function createCategoryBarChart() {
    const ctx = document.getElementById('categoryBarChart');
    if (!ctx) return;
    
    charts.categoryBar = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: categoryChartData.labels,
            datasets: [{
                label: 'Revenue',
                data: categoryChartData.values,
                backgroundColor: [
                    'rgba(157, 170, 242, 0.8)',
                    'rgba(255, 106, 61, 0.8)',
                    'rgba(244, 219, 125, 0.8)',
                    'rgba(16, 185, 129, 0.8)',
                    'rgba(167, 139, 250, 0.8)'
                ],
                borderColor: [
                    '#9daaf2',
                    '#ff6a3d',
                    '#f4db7d',
                    '#10b981',
                    '#a78bfa'
                ],
                borderWidth: 2,
                borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: '#1a2238',
                    titleColor: '#fff',
                    bodyColor: '#9daaf2',
                    borderColor: '#9daaf2',
                    borderWidth: 1,
                    padding: 12,
                    callbacks: {
                        label: (context) => 'Revenue: $' + context.parsed.y.toLocaleString()
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        color: '#6b7280',
                        callback: (value) => '$' + (value / 1000) + 'K'
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: '#6b7280'
                    }
                }
            }
        }
    });
}

function createCategoryPieChart() {
    const ctx = document.getElementById('categoryPieChart');
    if (!ctx) return;
    
    charts.categoryPie = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: categoryChartData.labels,
            datasets: [{
                data: categoryChartData.values,
                backgroundColor: [
                    '#9daaf2',
                    '#ff6a3d',
                    '#f4db7d',
                    '#10b981',
                    '#a78bfa'
                ],
                borderWidth: 0,
                hoverOffset: 10
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '65%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#374151',
                        padding: 15,
                        font: {
                            size: 12,
                            weight: '500'
                        },
                        usePointStyle: true
                    }
                },
                tooltip: {
                    backgroundColor: '#1a2238',
                    titleColor: '#fff',
                    bodyColor: '#9daaf2',
                    borderColor: '#9daaf2',
                    borderWidth: 1,
                    padding: 12,
                    callbacks: {
                        label: (context) => {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: $${value.toLocaleString()} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

// ============================================
// FORECAST CHART
// ============================================

function initializeForecastChart() {
    const ctx = document.getElementById('forecastChart');
    if (!ctx) return;
    
    charts.forecast = new Chart(ctx, {
        type: 'line',
        data: {
            labels: forecastChartData.labels,
            datasets: [
                {
                    label: 'Historical Sales',
                    data: forecastChartData.historical,
                    borderColor: '#9daaf2',
                    backgroundColor: 'rgba(157, 170, 242, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#9daaf2',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointRadius: 4
                },
                {
                    label: 'Predicted Sales',
                    data: forecastChartData.predicted,
                    borderColor: '#ff6a3d',
                    backgroundColor: 'rgba(255, 106, 61, 0.1)',
                    borderWidth: 3,
                    borderDash: [5, 5],
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#ff6a3d',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        color: '#374151',
                        font: {
                            size: 12,
                            weight: '500'
                        }
                    }
                },
                tooltip: {
                    backgroundColor: '#1a2238',
                    titleColor: '#fff',
                    bodyColor: '#9daaf2',
                    borderColor: '#9daaf2',
                    borderWidth: 1,
                    padding: 12,
                    callbacks: {
                        label: (context) => context.dataset.label + ': $' + context.parsed.y.toLocaleString()
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        color: '#6b7280',
                        callback: (value) => '$' + (value / 1000) + 'K'
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: '#6b7280'
                    }
                }
            }
        }
    });
}

// ============================================
// DATE-WISE REPORT GENERATION
// ============================================

function generateReport(event) {
    event.preventDefault();
    
    const dateFrom = document.getElementById('dateFrom').value;
    const dateTo = document.getElementById('dateTo').value;
    
    if (!dateFrom || !dateTo) {
        alert('Please select both dates');
        return;
    }
    
    if (new Date(dateFrom) > new Date(dateTo)) {
        alert('From date must be before To date');
        return;
    }
    
    // Show loading state
    const resultsDiv = document.getElementById('reportResults');
    resultsDiv.classList.remove('hidden');
    
    // Send request to Flask backend
    fetch('/api/generate-report', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            date_from: dateFrom,
            date_to: dateTo
        })
    })
    .then(response => response.json())
    .then(data => {
        // Update KPI values
        document.getElementById('reportSales').textContent = data.sales;
        document.getElementById('reportProfit').textContent = data.profit;
        document.getElementById('reportTopProduct').textContent = data.top_product;
        document.getElementById('reportWorstProduct').textContent = data.worst_product;
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to generate report. Please try again.');
    });
}

// ============================================
// DOWNLOAD FUNCTIONS
// ============================================

function downloadPDF() {
    const dateFrom = document.getElementById('dateFrom').value;
    const dateTo = document.getElementById('dateTo').value;
    
    window.location.href = `/api/download-pdf?date_from=${dateFrom}&date_to=${dateTo}`;
}

function downloadExcel() {
    const dateFrom = document.getElementById('dateFrom').value;
    const dateTo = document.getElementById('dateTo').value;
    
    window.location.href = `/api/download-excel?date_from=${dateFrom}&date_to=${dateTo}`;
}

// ============================================
// PASSWORD CHANGE
// ============================================

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

            // Clear fields
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

// ============================================
// LOGOUT
// ============================================

function logout() {
    if (confirm('Are you sure you want to logout?')) {
        window.location.href = '/logout';
    }
}

// ============================================
// MOBILE SIDEBAR TOGGLE
// ============================================

function toggleSidebar() {
    document.querySelector('.sidebar').classList.toggle('active');
}

// Add mobile menu button if needed
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
fetch("/api/monthly-sales")
    .then(res => res.json())
    .then(data => {
        if (!data.success) return;

        const ctx = document.getElementById("monthlySalesChart");

        new Chart(ctx, {
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
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    })
    .catch(err => console.error("Monthly chart error:", err));
// ============================================
// RESPONSIVE BEHAVIOR
// ============================================

window.addEventListener('resize', () => {
    if (window.innerWidth > 1024) {
        document.querySelector('.sidebar').classList.remove('active');
    }
});

console.log('✅ Retail Sense Dashboard Initialized');
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

            // 🔥 force redraw
            setTimeout(() => chart.resize(), 100);
        });
});
