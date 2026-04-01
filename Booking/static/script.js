// Конфигурация
const API_BASE = '';
let currentUser = null;

// Инициализация при загрузке
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    setupEventListeners();
    loadInitialData();
});

// Проверка соединения с API
async function checkApiConnection() {
    try {
        const response = await fetch(`${API_BASE}/`);
        if (response.ok) {
            console.log('✅ API connection OK');
            return true;
        } else {
            console.error('❌ API returned status:', response.status);
            return false;
        }
    } catch (error) {
        console.error('❌ Cannot connect to API:', error);
        return false;
    }
}

// Вызвать при загрузке
checkApiConnection();

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
    document.getElementById('makeAdminBtn').addEventListener('click', async () => {
        const targetUserId = document.getElementById('targetUserId').value;
        const isAdmin = document.getElementById('setAdminFlag').checked;
        const resultDiv = document.getElementById('makeAdminResult');

        if (!targetUserId) {
            resultDiv.innerHTML = '<div class="error">Введите ID пользователя</div>';
            return;
        }

        try {
            const response = await fetch(`${API_BASE}/auth/make-admin`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    admin_user_id: currentUser.user_id,
                    target_user_id: parseInt(targetUserId),
                    is_admin: isAdmin
                })
            });

            const data = await response.json();

            if (response.ok) {
                resultDiv.innerHTML = `<div class="success">✅ ${data.message}</div>`;
                document.getElementById('targetUserId').value = '';
            } else {
                resultDiv.innerHTML = `<div class="error">❌ ${data.detail || 'Ошибка'}</div>`;
            }
        } catch (error) {
            resultDiv.innerHTML = '<div class="error">Ошибка соединения</div>';
        }
    });
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

// Вспомогательные функции для управления вкладками
function showTab(tabName) {
    const btn = document.querySelector(`.tab-btn[data-tab="${tabName}"]`);
    const content = document.getElementById(`${tabName}Tab`);
    if (btn) btn.style.display = ''; // Сброс стиля (возврат к CSS)
    if (content) content.style.display = '';
}

function hideTab(tabName) {
    const btn = document.querySelector(`.tab-btn[data-tab="${tabName}"]`);
    const content = document.getElementById(`${tabName}Tab`);
    if (btn) btn.style.display = 'none';
    if (content) content.style.display = 'none';
}

// Обновление UI авторизации и прав доступа
function updateAuthUI() {
    // Списки вкладок по уровням доступа
    const adminTabs = ['forecast', 'discounts', 'admin']; // Только админ
    const userTabs = ['myBookings']; // Требуют авторизации (обычный юзер + админ)
    const publicTabs = ['bookings']; // Доступны всем (гостям и юзерам)

    if (currentUser) {
        // Пользователь авторизован
        document.getElementById('userDisplay').textContent = currentUser.fio || `ID: ${currentUser.user_id}`;
        document.getElementById('loginBtn').style.display = 'none';
        document.getElementById('logoutBtn').style.display = 'block';

        if (currentUser.is_admin) {
            // АДМИНИСТРАТОР: Видит все вкладки
            [...adminTabs, ...userTabs, ...publicTabs].forEach(tabName => showTab(tabName));
        } else {
            // ОБЫЧНЫЙ ПОЛЬЗОВАТЕЛЬ: Видит Бронирование и Мои брони
            [...userTabs, ...publicTabs].forEach(tabName => showTab(tabName));
            adminTabs.forEach(tabName => hideTab(tabName));
        }
    } else {
        // НЕ АВТОРИЗОВАН: Видит только Бронирование
        document.getElementById('userDisplay').textContent = 'Не авторизован';
        document.getElementById('loginBtn').style.display = 'block';
        document.getElementById('logoutBtn').style.display = 'none';

        publicTabs.forEach(tabName => showTab(tabName));
        [...adminTabs, ...userTabs].forEach(tabName => hideTab(tabName));
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
            currentUser = {
                user_id: data.user_id,
                is_admin: data.is_admin,
                fio: data.fio
            };
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
                        ${isAvailable ? `<button class="book-btn" onclick="bookSlot('${data.date}', '${slot.time_slot}', ${machineData.machine_number})">Забронировать</button>` : '<span class="booked-label">Занято</span>'}
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
        console.log('Sending forecast request:', {
            date: formattedDate,
            period: period,
            apply_discounts: applyDiscounts
        });

        const response = await fetch(`${API_BASE}/bookings/prophet/forecast`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({
                date: formattedDate,
                period: period,
                apply_discounts: applyDiscounts
            })
        });

        console.log('Response status:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.log('Error response:', errorText);
            try {
                const errorData = JSON.parse(errorText);
                resultDiv.innerHTML = `<div class="error">❌ ${errorData.detail || 'Ошибка получения прогноза'}</div>`;
            } catch {
                resultDiv.innerHTML = `<div class="error">❌ Ошибка ${response.status}: ${response.statusText}</div>`;
            }
            return;
        }

        const data = await response.json();
        console.log('Forecast data received:', data);
        
        if (data.error) {
            resultDiv.innerHTML = `<div class="error">❌ ${data.error}</div>`;
            return;
        }
        
        // Проверяем структуру ответа и рендерим соответственно
        renderForecast(data, period);
        
    } catch (error) {
        console.error('Connection error:', error);
        resultDiv.innerHTML = '<div class="error">❌ Ошибка соединения с сервером. Проверьте, запущен ли сервер (http://127.0.0.1:8000)</div>';
    }
}

// Отображение прогноза
function renderForecast(data, period) {
    const resultDiv = document.getElementById('forecastResult'); 
    if (!data) {
        resultDiv.innerHTML = '<div class="error">❌ Нет данных от сервера</div>';
        return;
    }

    console.log('Rendering forecast. Period:', period);
    console.log('Data received:', data);
    
    let html = '';
    
    if (period === 'day') {
        // Определяем, в каком формате пришли данные
        let predictionData = data;
        let discounts = [];
        
        // Если есть поле prediction, значит это формат со скидками
        if (data.prediction) {
            predictionData = data.prediction;
            discounts = data.discounts_created || [];
        }
        
        // Проверяем, что есть слоты
        if (predictionData.slots && Array.isArray(predictionData.slots)) {
            const pred = predictionData;
            
            // Создаем карту скидок для быстрого доступа
            const discountMap = {};
            discounts.forEach(d => {
                discountMap[d.time_slot] = d.discount;
            });
            
            // Определяем общее количество прогноза
            const totalPredicted = pred.total_predicted || 
                                   pred.slots.reduce((sum, slot) => sum + (slot.predicted_bookings || 0), 0).toFixed(2);
            
            html = `
                <div class="forecast-card">
                    <div class="forecast-header">
                        <h3>Прогноз на ${pred.date || data.date || 'неизвестную дату'}</h3>
                        <div class="forecast-day-info">${pred.day_of_week || ''}</div>
                    </div>
                    
                    <div class="forecast-summary">
                        <div class="summary-item">
                            <span class="summary-label">Всего прогноз:</span>
                            <span class="summary-value">${totalPredicted} броней</span>
                        </div>
                        ${data.slots_with_discount ? `
                        <div class="summary-item">
                            <span class="summary-label">Скидок применено:</span>
                            <span class="summary-value">${data.slots_with_discount} слотов</span>
                        </div>
                        ` : ''}
                    </div>
                    
                    <div class="forecast-slots">
            `;

            pred.slots.forEach(slot => {
                const loadClass = slot.load_level || 'medium';
                const discount = discountMap[slot.time_slot];
                
                // Определяем цвет фона в зависимости от загрузки
                let bgColor = '';
                if (loadClass === 'high') bgColor = '#fed7d7';
                else if (loadClass === 'medium') bgColor = '#feebc8';
                else bgColor = '#c6f6d5';
                
                // Определяем границы доверительного интервала
                const bounds = (slot.lower_bound !== undefined && slot.upper_bound !== undefined) 
                    ? `(${slot.lower_bound}-${slot.upper_bound})` 
                    : '';
                
                html += `
                    <div class="forecast-slot" style="background-color: ${bgColor}; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid ${loadClass === 'high' ? '#f56565' : loadClass === 'medium' ? '#ed8936' : '#48bb78'}">
                        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                            <div style="flex: 1;">
                                <strong style="font-size: 16px;">${slot.time_slot}</strong>
                                <div style="font-size: 14px; color: #4a5568; margin-top: 5px;">
                                    <div>Прогноз: ${slot.predicted_bookings} броней ${bounds}</div>
                                    ${slot.lower_bound !== undefined ? `
                                    <div style="font-size: 12px; color: #718096;">
                                        Доверительный интервал: ${slot.lower_bound.toFixed(2)} - ${slot.upper_bound.toFixed(2)}
                                    </div>
                                    ` : ''}
                                </div>
                            </div>
                            <div style="text-align: right; min-width: 150px;">
                                <div style="font-size: 20px; font-weight: bold; color: ${loadClass === 'high' ? '#c53030' : loadClass === 'medium' ? '#b7791f' : '#2f8555'}">
                                    ${slot.occupancy_percent}% загрузка
                                </div>
                                ${discount ? `
                                    <div style="background: #fbbf24; padding: 5px 15px; border-radius: 20px; font-weight: bold; margin-top: 8px; display: inline-block;">
                                        🔥 Скидка -${discount}%
                                    </div>
                                ` : data.apply_discounts === false ? `
                                    <div style="background: #e2e8f0; padding: 5px 15px; border-radius: 20px; margin-top: 8px; display: inline-block; color: #718096;">
                                        Без скидки
                                    </div>
                                ` : ''}
                            </div>
                        </div>
                    </div>
                `;
            });

            html += `
                    </div>
                    
                    <div class="forecast-footer" style="margin-top: 25px; padding: 15px; background: #f7fafc; border-radius: 8px; font-size: 14px; color: #4a5568;">
                        <div style="display: flex; gap: 20px; flex-wrap: wrap;">
                            <div><strong>Метод:</strong> ${data.model_info?.type || pred.model_info?.type || 'Prophet'}</div>
                            <div><strong>Всего слотов:</strong> ${pred.slots.length}</div>
                            ${data.used_fallback !== undefined ? `<div><strong>Fallback:</strong> ${data.used_fallback ? 'Да' : 'Нет'}</div>` : ''}
                        </div>
                        ${data.message ? `<div style="margin-top: 10px; color: #48bb78;">✅ ${data.message}</div>` : ''}
                    </div>
                </div>
            `;
            
        } else {
            // Если структура не распознана, покажем сырые данные
            html = `
                <div class="error" style="background: #fff5f5; padding: 20px; border-radius: 8px;">
                    <h4 style="color: #c53030; margin-bottom: 10px;">❌ Неизвестная структура данных</h4>
                    <p>Получен ответ от сервера, но он не содержит ожидаемых полей.</p>
                    <pre style="background: #f7fafc; padding: 15px; border-radius: 5px; overflow-x: auto; margin-top: 15px;">${JSON.stringify(data, null, 2)}</pre>
                </div>
            `;
        }
    } else {
        // Прогноз на неделю/месяц
        if (data.predictions && Array.isArray(data.predictions)) {
            html = `
                <div class="forecast-period-card">
                    <h3 style="color: #2d3748; margin-bottom: 20px;">📊 Прогноз на ${data.period || period}</h3>
                    
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0;">
                        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px;">
                            <div style="font-size: 14px; opacity: 0.9;">Всего прогноз</div>
                            <div style="font-size: 32px; font-weight: bold;">${data.total_predicted}</div>
                        </div>
                        <div style="background: linear-gradient(135deg, #48bb78 0%, #2f8555 100%); color: white; padding: 20px; border-radius: 10px;">
                            <div style="font-size: 14px; opacity: 0.9;">В среднем в день</div>
                            <div style="font-size: 32px; font-weight: bold;">${data.avg_per_day}</div>
                        </div>
                    </div>
                    
                    <h4 style="color: #4a5568; margin: 20px 0 10px;">📅 Прогноз по дням:</h4>
                    <div style="display: grid; gap: 10px;">
            `;

            data.predictions.forEach(day => {
                const percentOfAvg = ((day.total_predicted / data.avg_per_day) * 100).toFixed(0);
                html += `
                    <div style="background: #f7fafc; padding: 15px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; border-left: 4px solid ${day.total_predicted > data.avg_per_day ? '#48bb78' : '#f56565'}">
                        <div>
                            <strong style="font-size: 16px;">${day.date}</strong>
                            <span style="margin-left: 10px; color: #718096; font-size: 14px;">${day.day_of_week || ''}</span>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-weight: bold; font-size: 18px; color: ${day.total_predicted > data.avg_per_day ? '#2f8555' : '#c53030'}">
                                ${day.total_predicted} броней
                            </div>
                            <div style="font-size: 12px; color: #718096;">
                                ${percentOfAvg}% от среднего
                            </div>
                        </div>
                    </div>
                `;
            });

            html += `
                    </div>
                    
                    ${data.fallback_used !== undefined ? `
                    <div style="margin-top: 20px; padding: 15px; background: #f7fafc; border-radius: 8px; display: flex; gap: 20px; font-size: 14px;">
                        <div><strong>Prophet:</strong> ${data.prophet_used} дней</div>
                        <div><strong>Fallback:</strong> ${data.fallback_used} дней</div>
                        <div><strong>Точность:</strong> ${((data.prophet_used / data.days) * 100).toFixed(1)}%</div>
                    </div>
                    ` : ''}
                </div>
            `;
            
        } else {
            html = `
                <div class="error" style="background: #fff5f5; padding: 20px; border-radius: 8px;">
                    <h4 style="color: #c53030;">❌ Неверный формат данных для прогноза на период</h4>
                    <pre style="background: #f7fafc; padding: 15px; border-radius: 5px; margin-top: 10px;">${JSON.stringify(data, null, 2)}</pre>
                </div>
            `;
        }
    }
    
    resultDiv.innerHTML = html;
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
        const response = await fetch(`${API_BASE}/bookings/discounts/clear`, {
            method: 'POST',  // Ваш маршрут использует POST, не DELETE
            headers: {
                'Content-Type': 'application/json',
                'accept': 'application/json'
            }
            // Не отправляем date, чтобы удалить все
        });

        const data = await response.json();

        if (response.ok) {
            showNotification(`✅ ${data.message}. Удалено: ${data.deleted_count}`, 'success');
            loadDiscounts(); // Обновляем список скидок
        } else {
            showNotification(`❌ ${data.detail || 'Ошибка при удалении'}`, 'error');
        }
    } catch (error) {
        console.error('Error clearing discounts:', error);
        showNotification('❌ Ошибка соединения с сервером', 'error');
    }
}

// Обучение модели
async function trainModel() {
    const statusDiv = document.getElementById('modelStatus');
    statusDiv.innerHTML = 'Обучение модели...';
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