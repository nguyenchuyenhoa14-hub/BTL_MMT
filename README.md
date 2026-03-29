# BTL Mạng Máy Tính - Hybrid P2P Chat Application

Ứng dụng chat kết hợp hai mô hình:
1. **Client-Server**: Quản lý đăng nhập, phát hiện mạng (Tracker) và chat đa luồng (Channels).
2. **Peer-to-Peer (P2P)**: Nhắn tin riêng tư trực tiếp giữa hai máy bằng TCP sockets (Direct Message - DM).

## 1. Yêu cầu hệ thống
- Python 3.x
- Không cần thư viện ngoài (sử dụng base libraries socket, urllib, v.v.)

---

## 2. Hướng dẫn chạy thử (Demo Local)

Để mô phỏng môi trường mạng gồm nhiều máy tính, chúng ta sẽ mở nhiều cửa sổ terminal/dòng lệnh.

### Bước 1: Khởi động Tracker (Máy chủ trung tâm)
Mở Terminal thứ 1 và chạy lệnh sau:
```bash
python3 start_tracker.py --port 8000
```

### Bước 2: Khởi động Client 1 (Đóng vai trò "Máy Admin")
Mở Terminal thứ 2 và chạy lệnh:
```bash
python3 start_chatapp.py --port 8001 --p2p-port 5001 --tracker http://localhost:8000
```
- **URL trên trình duyệt:** `http://localhost:8001/chat.html`
- **Tài khoản test:** `admin`
- **Mật khẩu:** `admin123`

### Bước 3: Khởi động Client 2 (Đóng vai trò "Máy User 1")
Mở Terminal thứ 3 và chạy lệnh:
```bash
python3 start_chatapp.py --port 8002 --p2p-port 5002 --tracker http://localhost:8000
```
- **URL trên trình duyệt:** `http://localhost:8002/chat.html`
- **Tài khoản test:** `user1`
- **Mật khẩu:** `pass1`

### Tùy chọn: Thử nghiệm cùng lúc trên Điện thoại (Client 3)
Nếu bạn kết nối điện thoại vào cùng mạng Wifi với máy tính, mở thêm Terminal thứ 4 trên máy tính:
```bash
python3 start_chatapp.py --ip 0.0.0.0 --port 8003 --p2p-port 5003 --tracker http://localhost:8000
```
- Lấy IP mạng nội bộ của máy tính (ví dụ `192.168.1.5`)
- Trên điện thoại mở trình duyệt: `http://192.168.1.5:8003/chat.html`
- **Tài khoản test:** Bạn có thể điền đại một username/password bất kỳ (ví dụ `user2` / `pass2`) rồi bấm nút **Register** để tạo nhanh tài khoản sử dụng.

---

## 3. Cách nhận biết 2 mô hình Mạng

- 🔵 **Client-Server (Xanh Dương):** Nhấn `# general` ở sidebar. Các tin nhắn ở kênh này sẽ đi qua HTTP đến Server (Tracker), sau đó các Client khác tự động fetch ảnh về. Tất cả mọi người cùng thấy thông điệp trên kênh này.  
- 🟢 **P2P Socket (Xanh Lá cây):** Trên sidebar chỗ khung *Online (from tracker)*, bấm vào tên của một user. Cửa sổ chat riêng sẽ mở ra, ứng dụng sẽ thiết lập **kết nối TCP trực tiếp** đến cổng P2P của user bên kia (VD gửi thẳng vô cổng 5002). Tracker không hề giữ tin nhắn đó, chỉ đúng 2 người thiết lập luồng TCP này mới nhìn thấy.
