
const notificationBtn = document.getElementById("notifications-button");

notificationBtn.addEventListener('click', ()=>  Notification.requestPermission().then((permission) => {
    if (permission === "granted") {
      notificationBtn.textContent = "🔔 Enabled";
      new Notification("Example Notification from MyeGPT");
    } else {
      notificationBtn.textContent = "🔔 Disabled";
    }
  })
);