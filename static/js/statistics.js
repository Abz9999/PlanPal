document.addEventListener("DOMContentLoaded", initialiseStatisticsPage);

function initialiseStatisticsPage() {
  renderCategoryBreakdownChart();
  renderTrendCharts();
}

function renderCategoryBreakdownChart() {
  const categoryDataElement = document.getElementById("stats-categories-data");
  const categoryChartElement = document.getElementById("categoryDonut");

  if (!categoryDataElement || !categoryChartElement) {
    return;
  }

  const categories = parseCategoryData(categoryDataElement);

  if (categories.length === 0) {
    return;
  }

  new Chart(categoryChartElement, buildCategoryChartConfig(categories));
}

function renderTrendCharts() {
  const trendsDataElement = document.getElementById("stats-trends-data");

  if (!trendsDataElement) {
    return;
  }

  const trends = parseJsonData(trendsDataElement);

  if (trends.length === 0) {
    return;
  }

  renderCompletionTrendChart(trends);
  renderHoursTrendChart(trends);
}

function parseJsonData(dataElement) {
  try {
    return JSON.parse(dataElement.textContent);
  } catch (error) {
    return [];
  }
}

function parseCategoryData(categoryDataElement) {
  try {
    return JSON.parse(categoryDataElement.textContent);
  } catch (error) {
    return [];
  }
}

function buildCategoryChartConfig(categories) {
  return {
    type: "doughnut",
    data: {
      labels: categories.map(getCategoryName),
      datasets: [buildCategoryDataset(categories)],
    },
    options: {
      responsive: false,
      plugins: {
        legend: {
          display: false,
        },
      },
    },
  };
}

function buildCategoryDataset(categories) {
  return {
    data: categories.map(getCategoryHours),
    backgroundColor: categories.map(getCategoryColour),
  };
}

function renderCompletionTrendChart(trends) {
  const completionChartElement = document.getElementById("trendCompletion");

  if (!completionChartElement) {
    return;
  }

  new Chart(completionChartElement, buildCompletionTrendConfig(trends));
}

function renderHoursTrendChart(trends) {
  const hoursChartElement = document.getElementById("trendHours");

  if (!hoursChartElement) {
    return;
  }

  new Chart(hoursChartElement, buildHoursTrendConfig(trends));
}

function buildCompletionTrendConfig(trends) {
  return {
    type: "line",
    data: {
      labels: trends.map(getTrendLabel),
      datasets: [buildCompletionTrendDataset(trends)],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          min: 0,
          max: 100,
        },
      },
    },
  };
}

function buildHoursTrendConfig(trends) {
  return {
    type: "line",
    data: {
      labels: trends.map(getTrendLabel),
      datasets: [buildHoursTrendDataset(trends)],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          min: 0,
        },
      },
    },
  };
}

function buildCompletionTrendDataset(trends) {
  return {
    label: "Completion %",
    data: trends.map(getTrendCompletionPercentage),
    borderColor: "#276749",
    backgroundColor: "rgba(39, 103, 73, 0.1)",
    fill: true,
    tension: 0.3,
  };
}

function buildHoursTrendDataset(trends) {
  return {
    label: "Hours",
    data: trends.map(getTrendHours),
    borderColor: "#2b6cb0",
    backgroundColor: "rgba(43, 108, 176, 0.1)",
    fill: true,
    tension: 0.3,
  };
}

function getCategoryName(category) {
  return category.name;
}

function getCategoryHours(category) {
  return category.hours;
}

function getCategoryColour(category) {
  return category.colour;
}

function getTrendLabel(trend) {
  return trend.label;
}

function getTrendCompletionPercentage(trend) {
  return trend.completion_pct;
}

function getTrendHours(trend) {
  return trend.hours;
}