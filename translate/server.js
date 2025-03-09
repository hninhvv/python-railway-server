const express = require('express');
const app = express();
const port = 3000;

// Middleware để phân tích JSON
app.use(express.json());

// Dữ liệu mẫu
let users = [
    { id: 1, name: 'User 1', account: 'user1@example.com', password: 'password1', limited: 'Unlimited', status: 'Active', mac: '00:1A:2B:3C:4D:5E' },
    // Thêm dữ liệu khác nếu cần
];

// Middleware xác thực quyền admin
function adminAuth(req, res, next) {
    const adminToken = req.headers['admin-token'];
    if (adminToken === 'your_admin_token') {
        next();
    } else {
        res.status(403).send('Forbidden');
    }
}

// Endpoint để lấy danh sách người dùng
app.get('/api/users', adminAuth, (req, res) => {
    res.json(users);
});

// Endpoint để thêm người dùng mới
app.post('/api/users', adminAuth, (req, res) => {
    const newUser = req.body;
    users.push(newUser);
    res.status(201).json(newUser);
});

// Endpoint để cập nhật người dùng
app.put('/api/users/:id', adminAuth, (req, res) => {
    const userId = parseInt(req.params.id);
    const updatedUser = req.body;
    users = users.map(user => (user.id === userId ? updatedUser : user));
    res.json(updatedUser);
});

// Endpoint để xóa người dùng
app.delete('/api/users/:id', adminAuth, (req, res) => {
    const userId = parseInt(req.params.id);
    users = users.filter(user => user.id !== userId);
    res.status(204).send();
});

app.listen(port, () => {
    console.log(`API server running at http://localhost:${port}`);
});
