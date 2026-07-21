const timeElement = document.querySelector("#current-time")
const dateElement = document.querySelector("#current-date")
const weatherElement = document.querySelector(".weather")
const temperatureElement = document.querySelector("#temperature")
const descriptionElement = document.querySelector("#weather-description")
const locationElement = document.querySelector("#weather-location")
const iconElement = document.querySelector("#weather-icon-image")
const temperatureIconElement = document.querySelector("#temperature-icon")
const sunriseElement = document.querySelector("#sunrise-time")
const sunsetElement = document.querySelector("#sunset-time")

function updateClock() {
  const now = new Date()
  timeElement.textContent = new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(now)
  dateElement.textContent = new Intl.DateTimeFormat("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  }).format(now)
}

window.updateWeather = (payload) => {
  temperatureElement.textContent = payload.temperature || "--"
  descriptionElement.textContent = payload.description || "Weather unavailable"
  locationElement.textContent = payload.location || "Da Lat, Vietnam"
  sunriseElement.textContent = payload.sunrise || "--:--"
  sunsetElement.textContent = payload.sunset || "--:--"
  weatherElement.dataset.icon = payload.icon || ""
  weatherElement.dataset.daylight = payload.isDaylight ? "day" : "night"
  iconElement.src = payload.iconUrl || ""
  temperatureIconElement.src = payload.temperatureIconUrl || ""
}

updateClock()
window.setInterval(updateClock, 1000)
