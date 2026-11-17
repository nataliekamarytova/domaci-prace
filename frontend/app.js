let activeUserId = null;

async function loadUsers() {
  const users = await fetch("/api/users").then((r) => r.json());
  const tabs = document.getElementById("user-tabs");
  tabs.innerHTML = "";
  for (const user of users) {
    const button = document.createElement("button");
    button.textContent = user.name;
    button.classList.toggle("active", user.user_id === activeUserId);
    button.onclick = () => {
      activeUserId = user.user_id;
      refresh();
    };
    tabs.appendChild(button);
  }
  if (activeUserId === null && users.length > 0) {
    activeUserId = users[0].user_id;
  }
}

const FREQUENCY_LABELS = {
  daily: "denně",
  weekly: "týdně",
  monthly: "měsíčně",
  irregular: "nepravidelně",
};

async function loadChecklist() {
  const list = document.getElementById("task-list");
  if (activeUserId === null) {
    list.innerHTML = "";
    return;
  }
  const tasks = await fetch(`/api/checklist/${activeUserId}`).then((r) => r.json());
  list.innerHTML = "";
  for (const task of tasks) {
    const li = document.createElement("li");
    li.classList.toggle("done", task.done);
    li.classList.toggle("overdue", task.overdue && !task.done);

    const checkbox = document.createElement("button");
    checkbox.className = "checkbox";
    if (task.done) {
      checkbox.textContent = "✓";
      checkbox.disabled = true;
    } else {
      checkbox.onclick = () => completeTask(task.task_id);
    }
    li.appendChild(checkbox);

    const info = document.createElement("div");
    info.className = "task-info";

    const name = document.createElement("div");
    name.className = "task-name";
    name.textContent = task.name;
    info.appendChild(name);

    const meta = document.createElement("div");
    meta.className = "task-meta";

    const freqLabel = FREQUENCY_LABELS[task.frequency] ?? task.frequency;
    const freqBadge = document.createElement("span");
    freqBadge.className = "badge";
    freqBadge.textContent = freqLabel;
    meta.appendChild(freqBadge);

    const pointsBadge = document.createElement("span");
    pointsBadge.className = "badge points";
    pointsBadge.textContent = task.done
      ? `+${task.points_awarded} b.`
      : `${task.base_points} b.`;
    meta.appendChild(pointsBadge);

    if (task.done) {
      const statusBadge = document.createElement("span");
      statusBadge.className = "badge status-done";
      statusBadge.textContent = `splnil(a) ${task.completed_by}`;
      meta.appendChild(statusBadge);
    } else if (task.overdue) {
      const statusBadge = document.createElement("span");
      statusBadge.className = "badge status-overdue";
      statusBadge.textContent = "opožděno";
      meta.appendChild(statusBadge);
    } else if (!task.shared && task.completed_today.length > 0) {
      const summary = task.completed_today.map((e) => `${e.name} ${e.count}×`).join(", ");
      const statusBadge = document.createElement("span");
      statusBadge.className = "badge status-done";
      statusBadge.textContent = `dnes splněno: ${summary}`;
      meta.appendChild(statusBadge);
    }

    info.appendChild(meta);
    li.appendChild(info);

    list.appendChild(li);
  }
}

async function completeTask(taskId) {
  const response = await fetch(`/api/tasks/${taskId}/complete`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: activeUserId }),
  });
  if (!response.ok) {
    alert("Nepodařilo se splnit úkol - běží scoring služba na portu 8000?");
    return;
  }
  await refresh();
}

async function refresh() {
  await loadUsers();
  await loadChecklist();
}

refresh();
