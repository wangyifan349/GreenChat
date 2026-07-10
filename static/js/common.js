// Convert server-provided UTC timestamps into the browser's local time zone.
document.querySelectorAll("time[data-utc]").forEach((timeElement) => {
    const localDate = new Date(timeElement.dataset.utc);
    timeElement.textContent = Number.isNaN(localDate.getTime())
        ? ""
        : localDate.toLocaleString([], {
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
        });
});
