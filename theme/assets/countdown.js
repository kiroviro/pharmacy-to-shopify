(function () {
  const formatNumber = (number) => String(number).padStart(2, '0');
  const updateTimer = (timer, selector, value) => timer.querySelector(selector).innerText = formatNumber(value);

  const initTimer = () => {
    const currentTime = new Date().getTime();
    const countDownTimers = document.querySelectorAll(".countdown-bar-js");

    countDownTimers.forEach((timer) => {
      let { date: endDateStr, complited: completedCountdown } = timer.dataset;
      let endTime = new Date(endDateStr).getTime();
      let timeLeft = Math.max(endTime - currentTime, 0);

      if (timeLeft === 0 && completedCountdown === "hide_countdown") {
        timer.remove();
      } else if (timeLeft === 0 && completedCountdown === "cycle") {
        endTime = currentTime + 2.33 * 24 * 60 * 60 * 1000;
        timer.dataset.date = new Date(endTime).toISOString();
        timeLeft = Math.max(endTime - currentTime, 0);
      }

      const [days, hours, minutes, seconds] = [
        Math.floor(timeLeft / (1000 * 60 * 60 * 24)),
        Math.floor((timeLeft % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60)),
        Math.floor((timeLeft % (1000 * 60 * 60)) / (1000 * 60)),
        Math.floor((timeLeft % (1000 * 60)) / 1000)
      ];

      updateTimer(timer, ".countdown-bar__days .countdown-bar__number", days);
      updateTimer(timer, ".countdown-bar__hours .countdown-bar__number", hours);
      updateTimer(timer, ".countdown-bar__min .countdown-bar__number", minutes);
      updateTimer(timer, ".countdown-bar__sec .countdown-bar__number", seconds);
    });
  };

  let initTimerInterval;

  const startInterval = () => {
    if (!document.hidden) {
      initTimer();
      initTimerInterval = setInterval(initTimer, 1000);
    }
  };

  document.addEventListener("shopify:section:load", startInterval);
  startInterval();
})();