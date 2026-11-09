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

    const freqLabel = FREQUENCY_LABELS[task.frequency] ?? task.frequency;
    const label = document.createElement("span");
    if (task.done) {
      label.textContent = `✅ ${task.name} (${freqLabel}, ${task.points_awarded} b.) - splnil(a) ${task.completed_by}`;
    } else if (task.overdue) {
      label.textContent = `⚠️ ${task.name} (${freqLabel}, ${task.base_points} b.) - opožděno`;
      li.classList.add("overdue");
    } else {
      label.textContent = `${task.name} (${freqLabel}, ${task.base_points} b.)`;
    }
    li.appendChild(label);

    if (!task.done) {
      const button = document.createElement("button");
      button.textContent = "Hotovo";
      button.onclick = () => completeTask(task.task_id);
      li.appendChild(button);
    }

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
