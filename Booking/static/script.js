// Конфигурация
const API_BASE = '';
let currentUser = null;

// Инициализация при загрузке
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    setupEventListeners();
    loadInitialData();
});

// Настройка обработчиков событий
function setupEventListeners() {
    // Вкладки
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });

    // Авторизация
    document.getElementById('loginBtn').addEventListener('click', () => openModal('loginModal'));
    document.getElementById('logoutBtn').addEventListener('click', logout);
    document.getElementById('loginSubmitBtn').addEventListener('click', login);
    document.getElementById('showRegisterBtn').addEventListener('click', () => {
        closeModal('loginModal');
        openModal('registerModal');
    });
    document.getElementById('backToLoginBtn').addEventListener('click', () => {
        closeModal('registerModal');
        openModal('loginModal');
    });
    document.getElementById('registerSubmitBtn').addEventListener('click', register);

    // Закрытие модальных окон
    document.querySelectorAll('.close').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const modal = e.target.closest('.modal');
            if (modal) modal.style.display = 'none';
        });
    });

    // Бронирование
    document.getElementById('checkSlotsBtn').addEventListener('click', checkSlots);

    // Прогноз
    document.getElementById('getForecastBtn').addEventListener('click', getForecast);

    // Скидки
    document.getElementById('filterDiscountsBtn').addEventListener('click', loadDiscounts);
    document.getElementById('clearAllDiscountsBtn').addEventListener('click', clearAllDiscounts);

    // Администрирование
    document.getElementById('trainModelBtn').addEventListener('click', trainModel);
    document.getElementById('checkModelBtn').addEventListener('click', checkModelStatus);
    document.getElementById('clearAnalyticsBtn').addEventListener('click', clearAnalytics);
}

// Переключение вкладок
function switchTab(tabName) {
    // Обновляем активную кнопку
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });

    // Показываем нужный контент
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === `${tabName}Tab`);
    });

    // Загружаем данные для вкладки
    switch(tabName) {
        case 'myBookings':
            loadMyBookings();
            break;
        case 'discounts':
            loadDiscounts();
            break;
    }
}

// Проверка авторизации
function checkAuth() {
    const userStr = localStorage.getItem('user');
    if (userStr) {
        try {
            currentUser = JSON.parse(userStr);
            updateAuthUI();
        } catch (e) {
            localStorage.removeItem('user');
        }
    }
}

// Обновление UI авторизации
function updateAuthUI() {
    if (currentUser) {
        document.getElementById('userDisplay').textContent = currentUser.fio || `ID: ${currentUser.user_id}`;
        document.getElementById('loginBtn').style.display = 'none';
        document.getElementById('logoutBtn').style.display = 'block';
        
        // Показываем админ-вкладку для определенных пользователей
        if (currentUser.user_id === 1 || currentUser.user_id === 2) {
            document.getElementById('adminTab').style.display = 'block';
        }
    } else {
        document.getElementById('userDisplay').textContent = 'Не авторизован';
        document.getElementById('loginBtn').style.display = 'block';
        document.getElementById('logoutBtn').style.display = 'none';
        document.getElementById('adminTab').style.display = 'none';
    }
}

// Вход
async function login() {
    const phone = document.getElementById('loginPhone').value;
    const password = document.getElementById('loginPassword').value;
    
    try {
        const response = await fetch(`${API_BASE}/auth/signin`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ phone, password })
        });

        const data = await response.json();
        
        if (response.ok) {
            currentUser = { user_id: data.user_id };
            localStorage.setItem('user', JSON.stringify(currentUser));
            updateAuthUI();
            closeModal('loginModal');
            showNotification('Вход выполнен успешно', 'success');
            loadMyBookings();
        } else {
            document.getElementById('loginError').textContent = data.detail || 'Ошибка входа';
        }
    } catch (error) {
        document.getElementById('loginError').textContent = 'Ошибка соединения';
    }
}

// Регистрация
async function register() {
    const fio = document.getElementById('registerFio').value;
    const phone = document.getElementById('registerPhone').value;
    const password = document.getElementById('registerPassword').value;
    const confirm = document.getElementById('registerConfirmPassword').value;

    if (password !== confirm) {
        document.getElementById('registerError').textContent = 'Пароли не совпадают';
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/auth/signup`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fio, phone, password })
        });

        const data = await response.json();
        
        if (response.ok) {
            showNotification('Регистрация успешна! Теперь вы можете войти', 'success');
            closeModal('registerModal');
            openModal('loginModal');
        } else {
            document.getElementById('registerError').textContent = data.detail || 'Ошибка регистрации';
        }
    } catch (error) {
        document.getElementById('registerError').textContent = 'Ошибка соединения';
    }
}

// Выход
function logout() {
    currentUser = null;
    localStorage.removeItem('user');
    updateAuthUI();
    showNotification('Вы вышли из системы', 'info');
}

// Проверка доступных слотов
async function checkSlots() {
    const date = document.getElementById('bookingDate').value;
    if (!date) {
        showNotification('Выберите дату', 'warning');
        return;
    }

    const formattedDate = formatDateForAPI(date);
    document.getElementById('slotsContainer').innerHTML = '<div class="loading">Загрузка...</div>';

    try {
        const response = await fetch(`${API_BASE}/bookings/slots-with-discounts?selected_date=${formattedDate}`);
        const data = await response.json();

        if (response.ok) {
            renderSlots(data);
        } else {
            document.getElementById('slotsContainer').innerHTML = `<div class="error">${data.detail || 'Ошибка загрузки'}</div>`;
        }
    } catch (error) {
        document.getElementById('slotsContainer').innerHTML = '<div class="error">Ошибка соединения</div>';
    }
}

// Отображение слотов
function renderSlots(data) {
    const container = document.getElementById('slotsContainer');
    
    if (!data.machines || Object.keys(data.machines).length === 0) {
        container.innerHTML = '<div class="loading">Нет данных</div>';
        return;
    }

    let html = '';
    
    for (const [machineKey, machineData] of Object.entries(data.machines)) {
        html += `
            <div class="machine-card">
                <h3>Машина №${machineData.machine_number}</h3>
        `;

        machineData.available_slots.forEach(slot => {
            const isAvailable = slot.is_available;
            const discount = slot.discount || 0;
            
            html += `
                <div class="slot-item ${isAvailable ? 'available' : 'booked'}">
                    <span class="slot-time">${slot.time_slot}</span>
                    <div style="display: flex; gap: 10px; align-items: center;">
                        ${discount > 0 ? `<span class="slot-discount">-${discount}%</span>` : ''}
                        ${isAvailable ? '<button class="book-btn" onclick="bookSlot(\'' + data.date + '\', \'' + slot.time_slot + '\', ' + machineData.machine_number + ')">Забронировать</button>' : '<span class="booked-label">Занято</span>'}
                    </div>
                </div>
            `;
        });

        html += `</div>`;
    }

    container.innerHTML = html;
}

// Бронирование слота
async function bookSlot(date, timeSlot, machineNumber) {
    if (!currentUser) {
        showNotification('Необходимо войти в систему', 'warning');
        openModal('loginModal');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/bookings/book`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: currentUser.user_id,
                date: date,
                time_slot: timeSlot,
                machine_number: machineNumber
            })
        });

        const data = await response.json();

        if (response.ok) {
            showNotification('Бронирование успешно создано!', 'success');
            checkSlots(); // Обновляем слоты
            loadMyBookings(); // Обновляем список броней
        } else {
            showNotification(data.detail || 'Ошибка бронирования', 'error');
        }
    } catch (error) {
        showNotification('Ошибка соединения', 'error');
    }
}

// Загрузка моих броней
async function loadMyBookings() {
    const container = document.getElementById('myBookingsList');
    
    if (!currentUser) {
        container.innerHTML = '<div class="loading">Войдите в систему для просмотра броней</div>';
        return;
    }

    container.innerHTML = '<div class="loading">Загрузка...</div>';

    try {
        const response = await fetch(`${API_BASE}/bookings/my-bookings/${currentUser.user_id}`);
        const data = await response.json();

        if (response.ok) {
            renderMyBookings(data);
        } else {
            container.innerHTML = `<div class="error">${data.detail || 'Ошибка загрузки'}</div>`;
        }
    } catch (error) {
        container.innerHTML = '<div class="error">Ошибка соединения</div>';
    }
}

// Отображение моих броней
function renderMyBookings(data) {
    const container = document.getElementById('myBookingsList');
    
    if (!data.bookings || data.bookings.length === 0) {
        container.innerHTML = '<div class="loading">У вас нет бронирований</div>';
        return;
    }

    let html = '';
    
    data.bookings.forEach(booking => {
        html += `
            <div class="booking-card">
                <div class="booking-info">
                    <span class="booking-date">${booking.date}</span>
                    <span class="booking-slot">${booking.time_slot}</span>
                    <span class="booking-machine">Машина ${booking.machine_number}</span>
                </div>
                <button class="cancel-btn" onclick="cancelBooking(${booking.id})">Отменить</button>
            </div>
        `;
    });

    container.innerHTML = html;
}

// Отмена бронирования
async function cancelBooking(bookingId) {
    if (!confirm('Вы уверены, что хотите отменить бронирование?')) return;

    try {
        const response = await fetch(`${API_BASE}/bookings/delete/${bookingId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            showNotification('Бронирование отменено', 'success');
            loadMyBookings();
            checkSlots(); // Обновляем слоты если открыта вкладка бронирования
        } else {
            showNotification('Ошибка при отмене', 'error');
        }
    } catch (error) {
        showNotification('Ошибка соединения', 'error');
    }
}

// Получение прогноза
async function getForecast() {
    const date = document.getElementById('forecastDate').value;
    const period = document.getElementById('forecastPeriod').value;
    const applyDiscounts = document.getElementById('applyDiscounts').checked;

    if (!date) {
        showNotification('Выберите дату', 'warning');
        return;
    }

    const formattedDate = formatDateForAPI(date);
    const resultDiv = document.getElementById('forecastResult');
    resultDiv.innerHTML = '<div class="loading">Загрузка прогноза...</div>';

    try {
        const response = await fetch(`${API_BASE}/bookings/prophet/forecast`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                date: formattedDate,
                period: period,
                apply_discounts: applyDiscounts
            })
        });

        const data = await response.json();

        if (response.ok) {
            renderForecast(data, period);
        } else {
            resultDiv.innerHTML = `<div class="error">${data.detail || 'Ошибка получения прогноза'}</div>`;
        }
    } catch (error) {
        resultDiv.innerHTML = '<div class="error">Ошибка соединения</div>';
    }
}

// Отображение прогноза
function renderForecast(data, period) {
    const resultDiv = document.getElementById('forecastResult');
    
    if (period === 'day') {
        // Прогноз на один день
        let html = `
            <div class="forecast-day">
                <h4>${data.date} (${data.day_of_week})</h4>
                <div class="forecast-total">Всего прогноз: ${data.total_predicted} броней</div>
        `;

        data.slots.forEach(slot => {
            html += `
                <div class="forecast-slot ${slot.load_level}">
                    <span>${slot.time_slot}</span>
                    <span>${slot.predicted_bookings} броней (${slot.occupancy_percent}%)</span>
                </div>
            `;
        });

        html += `</div>`;
        resultDiv.innerHTML = html;
    } else {
        // Прогноз на неделю/месяц
        let html = `<h3>Прогноз на ${data.period}</h3>`;
        html += `<p>Всего прогноз: ${data.total_predicted} броней</p>`;
        html += `<p>В среднем в день: ${data.avg_per_day} броней</p>`;

        data.predictions.forEach(day => {
            html += `
                <div class="forecast-day">
                    <h4>${day.date} (${day.day_of_week}) - ${day.total_predicted} броней</h4>
                </div>
            `;
        });

        resultDiv.innerHTML = html;
    }
}

// Загрузка скидок
async function loadDiscounts() {
    const dateFilter = document.getElementById('discountDateFilter').value;
    const container = document.getElementById('discountsList');
    
    container.innerHTML = '<div class="loading">Загрузка...</div>';

    let url = `${API_BASE}/bookings/discounts`;
    if (dateFilter) {
        url += `?date=${formatDateForAPI(dateFilter)}`;
    }

    try {
        const response = await fetch(url);
        const data = await response.json();

        if (response.ok) {
            renderDiscounts(data);
        } else {
            container.innerHTML = `<div class="error">${data.detail || 'Ошибка загрузки'}</div>`;
        }
    } catch (error) {
        container.innerHTML = '<div class="error">Ошибка соединения</div>';
    }
}

// Отображение скидок
function renderDiscounts(data) {
    const container = document.getElementById('discountsList');
    
    if (!data.discounts || data.discounts.length === 0) {
        container.innerHTML = '<div class="loading">Нет активных скидок</div>';
        return;
    }

    let html = '';
    
    data.discounts.forEach(discount => {
        html += `
            <div class="discount-card">
                <div class="discount-info">
                    <span class="discount-date">${discount.date}</span>
                    <span class="discount-slot">${discount.time_slot}</span>
                    <span class="discount-percent">-${discount.discount_percent}%</span>
                    ${discount.machine_number ? `<span>Машина ${discount.machine_number}</span>` : '<span>Все машины</span>'}
                </div>
                <div class="discount-actions">
                    <button class="btn btn-secondary btn-small" onclick="editDiscount(${discount.id})">✏️</button>
                    <button class="btn btn-danger btn-small" onclick="deleteDiscount(${discount.id})">🗑️</button>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

// Редактирование скидки
async function editDiscount(discountId) {
    const newPercent = prompt('Введите новый процент скидки (0-100):');
    if (newPercent === null) return;

    const percent = parseInt(newPercent);
    if (isNaN(percent) || percent < 0 || percent > 100) {
        showNotification('Некорректное значение', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/bookings/discounts/${discountId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ discount_percent: percent })
        });

        if (response.ok) {
            showNotification('Скидка обновлена', 'success');
            loadDiscounts();
        } else {
            showNotification('Ошибка при обновлении', 'error');
        }
    } catch (error) {
        showNotification('Ошибка соединения', 'error');
    }
}

// Удаление скидки
async function deleteDiscount(discountId) {
    if (!confirm('Удалить эту скидку?')) return;

    try {
        const response = await fetch(`${API_BASE}/bookings/discounts/${discountId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            showNotification('Скидка удалена', 'success');
            loadDiscounts();
        } else {
            showNotification('Ошибка при удалении', 'error');
        }
    } catch (error) {
        showNotification('Ошибка соединения', 'error');
    }
}

// Очистка всех скидок
async function clearAllDiscounts() {
    if (!confirm('Вы уверены, что хотите удалить ВСЕ скидки?')) return;

    try {
        const response = await fetch(`${API_BASE}/bookings/discounts/clear/all?confirm=true`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (response.ok) {
            showNotification(`Удалено ${data.deleted_count} скидок`, 'success');
            loadDiscounts();
        } else {
            showNotification(data.detail || 'Ошибка при удалении', 'error');
        }
    } catch (error) {
        showNotification('Ошибка соединения', 'error');
    }
}

// Обучение модели
async function trainModel() {
    const statusDiv = document.getElementById('modelStatus');
    statusDiv.innerHTML = '<div class="loading">Обучение модели...</div>';

    try {
        const response = await fetch(`${API_BASE}/bookings/prophet/train?force_retrain=true`, {
            method: 'POST'
        });

        const data = await response.json();

        if (response.ok) {
            statusDiv.innerHTML = `<div class="success">✅ Модель обучена: ${data.data_points} точек данных (${data.date_range.from} - ${data.date_range.to})</div>`;
        } else {
            statusDiv.innerHTML = `<div class="error">❌ ${data.detail || 'Ошибка обучения'}</div>`;
        }
    } catch (error) {
        statusDiv.innerHTML = '<div class="error">Ошибка соединения</div>';
    }
}

// Проверка статуса модели
async function checkModelStatus() {
    const statusDiv = document.getElementById('modelStatus');

    try {
        const response = await fetch(`${API_BASE}/bookings/prophet/info`);
        const data = await response.json();

        if (response.ok) {
            if (data.status === 'active') {
                statusDiv.innerHTML = '<div class="success">✅ Модель активна и готова к работе</div>';
            } else {
                statusDiv.innerHTML = '<div class="warning">⚠️ Модель не обучена</div>';
            }
        } else {
            statusDiv.innerHTML = `<div class="error">${data.detail || 'Ошибка проверки'}</div>`;
        }
    } catch (error) {
        statusDiv.innerHTML = '<div class="error">Ошибка соединения</div>';
    }
}

// Очистка аналитики
async function clearAnalytics() {
    if (!confirm('ВНИМАНИЕ! Это удалит все данные аналитики. Продолжить?')) return;

    const resultDiv = document.getElementById('adminResult');
    resultDiv.innerHTML = '<div class="loading">Очистка...</div>';

    try {
        const response = await fetch(`${API_BASE}/analytics-data/clear/all?confirm=true`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (response.ok) {
            resultDiv.innerHTML = `<div class="success">✅ ${data.message}</div>`;
        } else {
            resultDiv.innerHTML = `<div class="error">❌ ${data.detail || 'Ошибка очистки'}</div>`;
        }
    } catch (error) {
        resultDiv.innerHTML = '<div class="error">Ошибка соединения</div>';
    }
}

// Вспомогательные функции
function openModal(modalId) {
    document.getElementById(modalId).style.display = 'block';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

function formatDateForAPI(dateStr) {
    const [year, month, day] = dateStr.split('-');
    return `${day}.${month}.${year}`;
}

function formatDateForInput(dateStr) {
    const [day, month, year] = dateStr.split('.');
    return `${year}-${month}-${day}`;
}

function showNotification(message, type) {
    // Простая реализация - можно заменить на красивые toast-уведомления
    alert(message);
}

// Загрузка начальных данных
function loadInitialData() {
    // Устанавливаем сегодняшнюю дату в поля ввода
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('bookingDate').value = today;
    document.getElementById('forecastDate').value = today;
}