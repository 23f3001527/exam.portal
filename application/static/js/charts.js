// Charts for Examination Statistics (Admin Dashboard)

function renderAdminCharts(chartData) {
    if (!chartData) return;

    // 1. Examination Completion & Booking Status Chart
    const statusCtx = document.getElementById('bookingStatusChart');
    if (statusCtx) {
        new Chart(statusCtx, {
            type: 'doughnut',
            data: {
                labels: ['Completed & Evaluated', 'Active / Upcoming', 'Cancelled'],
                datasets: [{
                    data: [
                        chartData.completed || 0,
                        chartData.active || 0,
                        chartData.cancelled || 0
                    ],
                    backgroundColor: ['#10b981', '#3b82f6', '#ef4444'],
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }

    // 2. Examiner Workload Chart (Slots & Bookings)
    const workloadCtx = document.getElementById('examinerWorkloadChart');
    if (workloadCtx) {
        const labels = (chartData.examiner_names && chartData.examiner_names.length > 0) 
            ? chartData.examiner_names 
            : ['No active examiners'];
        const slots = chartData.examiner_slots || [0];
        const bookings = chartData.examiner_bookings || [0];

        new Chart(workloadCtx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Slots Created',
                        data: slots,
                        backgroundColor: '#6366f1',
                        borderRadius: 4
                    },
                    {
                        label: 'Students Booked',
                        data: bookings,
                        backgroundColor: '#0ea5e9',
                        borderRadius: 4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { stepSize: 1 }
                    }
                },
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }
}

