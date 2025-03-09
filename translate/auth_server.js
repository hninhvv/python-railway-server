const express = require('express');
const bodyParser = require('body-parser');
const fs = require('fs');
const path = require('path');
const cors = require('cors');
const http = require('http');

const app = express();
const PORT = 5001
;

// Đường dẫn đến tệp lưu thông tin đăng nhập
const CREDENTIALS_FILE = path.join(__dirname, 'credentials.json');

// Đường dẫn đến tệp lưu thông tin người dùng
const USER_DATA_FILE = path.join(__dirname, 'user_data.json');

// Middleware để phân tích cú pháp JSON
app.use(bodyParser.json({ limit: '10mb' }));

// Cấu hình CORS chi tiết
app.use(cors({
    origin: '*', // Cho phép tất cả các nguồn
    methods: ['GET', 'POST', 'PUT', 'DELETE'],
    allowedHeaders: ['Content-Type', 'Authorization']
}));

// Thêm header CORS thủ công cho tất cả các route
app.use((req, res, next) => {
    res.header('Access-Control-Allow-Origin', '*');
    res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept, Authorization');
    res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
    if (req.method === 'OPTIONS') {
        return res.status(200).end();
    }
    next();
});

// Hàm tải thông tin đăng nhập từ tệp
function loadCredentials() {
    if (fs.existsSync(CREDENTIALS_FILE)) {
        const data = fs.readFileSync(CREDENTIALS_FILE, 'utf8');
        return JSON.parse(data);
    }
    return {};
}

// Hàm tải dữ liệu người dùng từ file
function loadUserData() {
    if (fs.existsSync(USER_DATA_FILE)) {
        try {
            const data = fs.readFileSync(USER_DATA_FILE, 'utf8');
            return JSON.parse(data);
        } catch (error) {
            console.error('Lỗi khi đọc file user_data.json:', error);
            return {
                usersWindows: [],
                usersMacOS: [],
                usersAndroid: [],
                usersIOS: []
            };
        }
    }
    return {
        usersWindows: [],
        usersMacOS: [],
        usersAndroid: [],
        usersIOS: []
    };
}

// Thêm biến để theo dõi phiên bản dữ liệu
let currentDataVersion = 0;

// Cập nhật hàm saveUserData để loại bỏ trường version trước khi lưu
function saveUserData(data) {
    // Tạo bản sao của dữ liệu để không ảnh hưởng đến dữ liệu gốc
    const dataCopy = JSON.parse(JSON.stringify(data));
    
    // Loại bỏ trường version nếu có
    delete dataCopy.version;
    
    fs.writeFileSync(USER_DATA_FILE, JSON.stringify(dataCopy, null, 2));
    console.log('Dữ liệu đã được lưu vào file user_data.json');
    
    // Đọc lại dữ liệu để xác nhận
    try {
        const savedData = JSON.parse(fs.readFileSync(USER_DATA_FILE, 'utf8'));
        console.log(`Đã lưu ${savedData.usersWindows.length} người dùng Windows, ${savedData.usersMacOS.length} người dùng MacOS, ${savedData.usersAndroid.length} người dùng Android, ${savedData.usersIOS.length} người dùng iOS`);
    } catch (error) {
        console.error('Lỗi khi đọc lại dữ liệu:', error);
    }
}

// Thêm endpoint kiểm tra trạng thái đồng bộ
app.get('/sync_status', (req, res) => {
    try {
        const userData = loadUserData();
        const stats = {
            usersWindows: userData.usersWindows.length,
            usersMacOS: userData.usersMacOS.length,
            usersAndroid: userData.usersAndroid.length,
            usersIOS: userData.usersIOS.length,
            lastSync: new Date().toISOString(),
            currentVersion: currentDataVersion
        };
        res.status(200).json({
            status: 'success',
            message: 'Trạng thái đồng bộ',
            stats: stats
        });
    } catch (error) {
        res.status(500).json({
            status: 'error',
            message: 'Lỗi khi kiểm tra trạng thái đồng bộ',
            error: error.message
        });
    }
});

// Cập nhật endpoint đồng bộ dữ liệu
app.post('/sync_data', (req, res) => {
    const userData = req.body;
    
    // Kiểm tra dữ liệu hợp lệ
    if (!userData) {
        return res.status(400).json({ status: 'error', message: 'Dữ liệu không hợp lệ' });
    }
    
    try {
        // Đọc dữ liệu hiện tại
        const currentData = loadUserData();
        
        // Kiểm tra phiên bản dữ liệu
        const dataVersion = userData.version || 0;
        
        // Xác định hệ điều hành đang được đồng bộ
        const syncingWindows = userData.hasOwnProperty('usersWindows');
        const syncingMacOS = userData.hasOwnProperty('usersMacOS');
        const syncingAndroid = userData.hasOwnProperty('usersAndroid');
        const syncingIOS = userData.hasOwnProperty('usersIOS');
        
        // Tạo dữ liệu mới bằng cách kết hợp dữ liệu hiện tại và dữ liệu mới
        const newData = {
            usersWindows: syncingWindows ? userData.usersWindows : currentData.usersWindows,
            usersMacOS: syncingMacOS ? userData.usersMacOS : currentData.usersMacOS,
            usersAndroid: syncingAndroid ? userData.usersAndroid : currentData.usersAndroid,
            usersIOS: syncingIOS ? userData.usersIOS : currentData.usersIOS
        };
        
        // Lưu dữ liệu mới
        saveUserData(newData);
        currentDataVersion = dataVersion > currentDataVersion ? dataVersion : currentDataVersion + 1;
        
        // Xác định hệ điều hành đã được đồng bộ
        const syncedOS = [];
        if (syncingWindows) syncedOS.push('Windows');
        if (syncingMacOS) syncedOS.push('MacOS');
        if (syncingAndroid) syncedOS.push('Android');
        if (syncingIOS) syncedOS.push('IOS');
        
        console.log(`Đồng bộ dữ liệu thành công (phiên bản ${currentDataVersion})`);
        console.log(`Đã đồng bộ: ${syncedOS.join(', ')}`);
        
        res.status(200).json({ 
            status: 'success', 
            message: 'Dữ liệu đã được đồng bộ', 
            timestamp: new Date().toISOString(),
            version: currentDataVersion,
            syncedOS: syncedOS,
            userCount: {
                windows: newData.usersWindows.length,
                macos: newData.usersMacOS.length,
                android: newData.usersAndroid.length,
                ios: newData.usersIOS.length
            }
        });
    } catch (error) {
        console.error('Lỗi khi đồng bộ dữ liệu:', error);
        res.status(500).json({ 
            status: 'error', 
            message: 'Lỗi khi đồng bộ dữ liệu', 
            error: error.message 
        });
    }
});

// Endpoint xác thực
app.post('/authenticate', (req, res) => {
    const { username, password } = req.body;
    console.log('Yêu cầu đăng nhập:', username);
    
    // Đọc dữ liệu người dùng
    const userData = loadUserData();
    
    // Kiểm tra trong tất cả các hệ điều hành
    for (const osType of ['usersWindows', 'usersMacOS', 'usersAndroid', 'usersIOS']) {
        const users = userData[osType] || [];
        const user = users.find(u => u.account === username && u.password === password);
        
        if (user) {
            // Kiểm tra trạng thái người dùng
            if (user.status === 'Active') {
                return res.status(200).json({ 
                    status: 'success', 
                    message: 'Đăng nhập thành công!',
                    user: {
                        name: user.name,
                        account: user.account,
                        limited: user.limited,
                        status: user.status,
                        ip: user.ip
                    }
                });
            } else {
                return res.status(401).json({ 
                    status: 'error', 
                    message: `Tài khoản của bạn đang ở trạng thái: ${user.status}` 
                });
            }
        }
    }
    
    // Nếu không tìm thấy người dùng
    res.status(401).json({ status: 'failure', message: 'Tên đăng nhập hoặc mật khẩu không đúng' });
});

// Endpoint lấy dữ liệu người dùng
app.get('/users', (req, res) => {
    const userData = loadUserData();
    res.status(200).json(userData);
});

// Endpoint kiểm tra trạng thái server
app.get('/', (req, res) => {
    res.send('Welcome to the authentication server!');
});

// Endpoint cập nhật địa chỉ IP
app.post('/update_ip', (req, res) => {
    const { account, ip } = req.body;
    const userData = loadUserData();
    
    for (const osType of ['usersWindows', 'usersMacOS', 'usersAndroid', 'usersIOS']) {
        const users = userData[osType] || [];
        const user = users.find(u => u.account === account);
        
        if (user) {
            user.ip = ip;
            saveUserData(userData);
            return res.status(200).json({ status: 'success', message: 'IP updated successfully' });
        }
    }
    
    res.status(404).json({ status: 'error', message: 'User not found' });
});

// Khởi động máy chủ
app.listen(PORT, () => {
    console.log(`Server is running on http://localhost:${PORT}`);
    
    // Tạo file user_data.json nếu chưa tồn tại
    if (!fs.existsSync(USER_DATA_FILE)) {
        const initialData = {
            usersWindows: [],
            usersMacOS: [],
            usersAndroid: [],
            usersIOS: []
        };
        saveUserData(initialData);
        console.log('Đã tạo file user_data.json');
    }
});

// Thêm endpoint cập nhật thông tin người dùng
app.post('/update_user/:userId', (req, res) => {
    const { userId } = req.params;
    const updatedData = req.body;
    
    if (!updatedData) {
        return res.status(400).json({ status: 'error', message: 'Dữ liệu không hợp lệ' });
    }
    
    try {
        const userData = loadUserData();
        let userFound = false;
        
        // Tìm và cập nhật người dùng trong tất cả các hệ điều hành
        for (const osType of ['usersWindows', 'usersMacOS', 'usersAndroid', 'usersIOS']) {
            const users = userData[osType] || [];
            const userIndex = users.findIndex(u => u.name === userId || u.account === userId);
            
            if (userIndex !== -1) {
                // Cập nhật thông tin người dùng
                userData[osType][userIndex] = {
                    ...userData[osType][userIndex],
                    ...updatedData
                };
                userFound = true;
                break;
            }
        }
        
        if (userFound) {
            saveUserData(userData);
            return res.status(200).json({ 
                status: 'success', 
                message: 'Cập nhật thông tin người dùng thành công' 
            });
        } else {
            return res.status(404).json({ 
                status: 'error', 
                message: 'Không tìm thấy người dùng' 
            });
        }
    } catch (error) {
        console.error('Lỗi khi cập nhật thông tin người dùng:', error);
        return res.status(500).json({ 
            status: 'error', 
            message: 'Lỗi khi cập nhật thông tin người dùng', 
            error: error.message 
        });
    }
});
