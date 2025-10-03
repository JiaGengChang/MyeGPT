
const notificationBtn = document.getElementById("notifications-button");

notificationBtn.addEventListener('click', ()=>  Notification.requestPermission().then((permission) => {
    if (permission === "granted") {
      if (window.innerWidth < 768) {
        notificationBtn.textContent = "🔔 On";
      } else {
        notificationBtn.textContent = "🔔 Enabled";
      }
      new Notification("Example Notification from MyeGPT");
    } else {
      if (window.innerWidth < 768) {
        notificationBtn.textContent = "🔕 Off";
      } else {
        notificationBtn.textContent = "🔕 Disabled";
      }
    }
  })
);