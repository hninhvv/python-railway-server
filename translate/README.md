# Server Xác Thực

Server API đơn giản được xây dựng bằng Flask để xác thực người dùng.

## Các API

- `GET /`: Kiểm tra trạng thái server
- `POST /authenticate`: Xác thực người dùng với username và password

## Cách sử dụng

### Kiểm tra trạng thái server

```
GET /
```

### Xác thực người dùng

```
POST /authenticate
Content-Type: application/json

{
  "username": "your_username",
  "password": "your_password"
}
```

## Triển khai

Server này được triển khai trên Railway.
