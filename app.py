import sqlite3
from datetime import datetime, date
from pathlib import Path

import pandas as pd
import streamlit as st


# ============================================================
# CẤU HÌNH ỨNG DỤNG
# ============================================================

APP_NAME = "QUẢN LÝ KHÁCH SẠN"
DB_PATH = Path(__file__).parent / "hotel.db"

st.set_page_config(
    page_title=APP_NAME,
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>
        .main {
            background-color: #f7f9fc;
        }

        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
        }

        .hotel-title {
            font-size: 2rem;
            font-weight: 700;
            color: #16324f;
            margin-bottom: 0.2rem;
        }

        .hotel-subtitle {
            color: #6b7280;
            margin-bottom: 1.5rem;
        }

        div[data-testid="stMetric"] {
            background-color: white;
            border-radius: 12px;
            padding: 15px;
            border: 1px solid #e5e7eb;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }

        .room-card {
            padding: 18px;
            border-radius: 14px;
            background: white;
            border: 1px solid #e5e7eb;
            margin-bottom: 12px;
        }

        .status-available {
            color: #15803d;
            font-weight: 700;
        }

        .status-occupied {
            color: #dc2626;
            font-weight: 700;
        }

        .status-maintenance {
            color: #d97706;
            font-weight: 700;
        }

        .sidebar-title {
            font-size: 1.1rem;
            font-weight: 700;
            color: #16324f;
        }

        .small-text {
            color: #6b7280;
            font-size: 0.85rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# DATABASE
# ============================================================

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def execute(query, params=(), fetch=False, many=False):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        if many:
            cursor.executemany(query, params)
        else:
            cursor.execute(query, params)

        if fetch:
            return cursor.fetchall()

        conn.commit()
        return cursor.lastrowid

    finally:
        conn.close()


def init_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_number TEXT UNIQUE NOT NULL,
            room_type TEXT NOT NULL,
            price REAL NOT NULL DEFAULT 0,
            floor INTEGER DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'Trống',
            note TEXT DEFAULT ''
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            id_number TEXT,
            address TEXT,
            created_at TEXT NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_code TEXT UNIQUE NOT NULL,
            customer_id INTEGER NOT NULL,
            room_id INTEGER NOT NULL,
            check_in TEXT NOT NULL,
            check_out TEXT NOT NULL,
            adults INTEGER DEFAULT 1,
            children INTEGER DEFAULT 0,
            room_price REAL NOT NULL,
            extra_charge REAL DEFAULT 0,
            discount REAL DEFAULT 0,
            total_amount REAL DEFAULT 0,
            deposit REAL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'Đã đặt',
            payment_status TEXT NOT NULL DEFAULT 'Chưa thanh toán',
            note TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY(customer_id) REFERENCES customers(id),
            FOREIGN KEY(room_id) REFERENCES rooms(id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            payment_method TEXT NOT NULL,
            payment_date TEXT NOT NULL,
            note TEXT DEFAULT '',
            FOREIGN KEY(booking_id) REFERENCES bookings(id)
        )
        """
    )

    conn.commit()

    # Tạo dữ liệu phòng mẫu nếu database còn trống
    count = cursor.execute("SELECT COUNT(*) FROM rooms").fetchone()[0]

    if count == 0:
        sample_rooms = [
            ("101", "Standard", 500000, 1),
            ("102", "Standard", 500000, 1),
            ("103", "Standard", 550000, 1),
            ("104", "Standard", 550000, 1),
            ("201", "Deluxe", 800000, 2),
            ("202", "Deluxe", 800000, 2),
            ("203", "Deluxe", 850000, 2),
            ("204", "Deluxe", 850000, 2),
            ("301", "Suite", 1200000, 3),
            ("302", "Suite", 1500000, 3),
        ]

        cursor.executemany(
            """
            INSERT INTO rooms
            (room_number, room_type, price, floor, status)
            VALUES (?, ?, ?, ?, 'Trống')
            """,
            sample_rooms,
        )

        conn.commit()

    conn.close()


# ============================================================
# HELPER
# ============================================================

def money(value):
    try:
        return f"{float(value):,.0f} ₫".replace(",", ".")
    except Exception:
        return "0 ₫"


def format_date(value):
    if not value:
        return ""

    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        return str(value)


def generate_booking_code():
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"BK{timestamp}"


def get_rooms(status=None):
    if status:
        return execute(
            """
            SELECT * FROM rooms
            WHERE status = ?
            ORDER BY room_number
            """,
            (status,),
            fetch=True,
        )

    return execute(
        "SELECT * FROM rooms ORDER BY room_number",
        fetch=True,
    )


def get_customers():
    return execute(
        """
        SELECT * FROM customers
        ORDER BY id DESC
        """,
        fetch=True,
    )


def get_bookings():
    return execute(
        """
        SELECT
            b.*,
            c.full_name AS customer_name,
            c.phone AS customer_phone,
            r.room_number,
            r.room_type
        FROM bookings b
        JOIN customers c ON b.customer_id = c.id
        JOIN rooms r ON b.room_id = r.id
        ORDER BY b.id DESC
        """,
        fetch=True,
    )


def get_booking_by_id(booking_id):
    rows = execute(
        """
        SELECT
            b.*,
            c.full_name AS customer_name,
            c.phone AS customer_phone,
            c.email AS customer_email,
            c.id_number,
            r.room_number,
            r.room_type
        FROM bookings b
        JOIN customers c ON b.customer_id = c.id
        JOIN rooms r ON b.room_id = r.id
        WHERE b.id = ?
        """,
        (booking_id,),
        fetch=True,
    )

    return rows[0] if rows else None


def calculate_total(room_price, check_in, check_out, extra_charge, discount):
    days = max((check_out - check_in).days, 1)
    room_total = room_price * days
    total = room_total + extra_charge - discount
    return days, max(total, 0)


# ============================================================
# DASHBOARD
# ============================================================

def dashboard():
    st.markdown(
        '<div class="hotel-title">🏨 Tổng quan khách sạn</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="hotel-subtitle">Theo dõi tình trạng phòng, đặt phòng và doanh thu</div>',
        unsafe_allow_html=True,
    )

    rooms = get_rooms()
    customers = get_customers()
    bookings = get_bookings()

    total_rooms = len(rooms)
    available_rooms = sum(1 for r in rooms if r["status"] == "Trống")
    occupied_rooms = sum(1 for r in rooms if r["status"] == "Đang ở")
    maintenance_rooms = sum(1 for r in rooms if r["status"] == "Bảo trì")

    today = date.today().isoformat()

    today_checkins = [
        b for b in bookings
        if b["check_in"] == today
    ]

    today_checkouts = [
        b for b in bookings
        if b["check_out"] == today
    ]

    total_revenue = sum(
        float(b["total_amount"] or 0)
        for b in bookings
        if b["status"] in ("Đã trả phòng", "Đang ở", "Đã nhận phòng")
    )

    st.subheader("Tình hình hôm nay")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Tổng số phòng",
        total_rooms,
    )

    col2.metric(
        "Phòng trống",
        available_rooms,
    )

    col3.metric(
        "Đang có khách",
        occupied_rooms,
    )

    col4.metric(
        "Bảo trì",
        maintenance_rooms,
    )

    st.divider()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Khách hàng",
        len(customers),
    )

    col2.metric(
        "Check-in hôm nay",
        len(today_checkins),
    )

    col3.metric(
        "Check-out hôm nay",
        len(today_checkouts),
    )

    col4.metric(
        "Tổng doanh thu",
        money(total_revenue),
    )

    st.divider()

    left, right = st.columns(2)

    with left:
        st.subheader("🛏️ Tình trạng phòng")

        if rooms:
            room_data = []

            for room in rooms:
                room_data.append(
                    {
                        "Phòng": room["room_number"],
                        "Loại": room["room_type"],
                        "Giá/đêm": money(room["price"]),
                        "Tầng": room["floor"],
                        "Trạng thái": room["status"],
                    }
                )

            st.dataframe(
                pd.DataFrame(room_data),
                use_container_width=True,
                hide_index=True,
            )

    with right:
        st.subheader("📅 Lịch nhận/trả phòng hôm nay")

        events = []

        for booking in bookings:
            if booking["check_in"] == today:
                events.append(
                    {
                        "Loại": "Nhận phòng",
                        "Phòng": booking["room_number"],
                        "Khách": booking["customer_name"],
                        "Thời gian": format_date(booking["check_in"]),
                    }
                )

            if booking["check_out"] == today:
                events.append(
                    {
                        "Loại": "Trả phòng",
                        "Phòng": booking["room_number"],
                        "Khách": booking["customer_name"],
                        "Thời gian": format_date(booking["check_out"]),
                    }
                )

        if events:
            st.dataframe(
                pd.DataFrame(events),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("Hôm nay chưa có lịch nhận/trả phòng.")


# ============================================================
# QUẢN LÝ PHÒNG
# ============================================================

def room_management():
    st.header("🛏️ Quản lý phòng")

    tab1, tab2 = st.tabs(
        ["Danh sách phòng", "Thêm phòng"]
    )

    with tab1:
        rooms = get_rooms()

        if rooms:
            data = []

            for room in rooms:
                data.append(
                    {
                        "ID": room["id"],
                        "Phòng": room["room_number"],
                        "Loại phòng": room["room_type"],
                        "Giá/đêm": room["price"],
                        "Tầng": room["floor"],
                        "Trạng thái": room["status"],
                        "Ghi chú": room["note"],
                    }
                )

            df = pd.DataFrame(data)

            search = st.text_input(
                "🔎 Tìm phòng",
                placeholder="Nhập số phòng hoặc loại phòng...",
            )

            if search:
                mask = (
                    df["Phòng"].astype(str).str.contains(
                        search, case=False, na=False
                    )
                    |
                    df["Loại phòng"].astype(str).str.contains(
                        search, case=False, na=False
                    )
                )
                df = df[mask]

            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Giá/đêm": st.column_config.NumberColumn(
                        format="%,.0f ₫"
                    )
                },
            )

            st.subheader("Cập nhật phòng")

            room_options = {
                f"{r['room_number']} - {r['room_type']}": r["id"]
                for r in rooms
            }

            selected = st.selectbox(
                "Chọn phòng",
                list(room_options.keys()),
            )

            selected_id = room_options[selected]

            room = next(
                r for r in rooms if r["id"] == selected_id
            )

            c1, c2, c3 = st.columns(3)

            with c1:
                new_type = st.selectbox(
                    "Loại phòng",
                    ["Standard", "Deluxe", "Suite", "Family", "VIP"],
                    index=(
                        ["Standard", "Deluxe", "Suite", "Family", "VIP"]
                        .index(room["room_type"])
                        if room["room_type"]
                        in ["Standard", "Deluxe", "Suite", "Family", "VIP"]
                        else 0
                    ),
                )

            with c2:
                new_price = st.number_input(
                    "Giá/đêm",
                    min_value=0.0,
                    value=float(room["price"]),
                    step=50000.0,
                )

            with c3:
                statuses = ["Trống", "Bảo trì"]

                # Nếu đang có khách thì không cho chuyển trực tiếp
                if room["status"] == "Đang ở":
                    statuses = ["Đang ở"]

                current_index = (
                    statuses.index(room["status"])
                    if room["status"] in statuses
                    else 0
                )

                new_status = st.selectbox(
                    "Trạng thái",
                    statuses,
                    index=current_index,
                )

            new_note = st.text_input(
                "Ghi chú",
                value=room["note"] or "",
            )

            if st.button(
                "💾 Cập nhật phòng",
                type="primary",
                use_container_width=True,
            ):
                execute(
                    """
                    UPDATE rooms
                    SET room_type = ?,
                        price = ?,
                        status = ?,
                        note = ?
                    WHERE id = ?
                    """,
                    (
                        new_type,
                        new_price,
                        new_status,
                        new_note,
                        selected_id,
                    ),
                )

                st.success("Đã cập nhật phòng.")
                st.rerun()

        else:
            st.info("Chưa có phòng.")

    with tab2:
        with st.form("add_room_form"):
            c1, c2 = st.columns(2)

            with c1:
                room_number = st.text_input(
                    "Số phòng *",
                    placeholder="Ví dụ: 401",
                )

                room_type = st.selectbox(
                    "Loại phòng",
                    [
                        "Standard",
                        "Deluxe",
                        "Suite",
                        "Family",
                        "VIP",
                    ],
                )

            with c2:
                price = st.number_input(
                    "Giá phòng/đêm *",
                    min_value=0.0,
                    value=500000.0,
                    step=50000.0,
                )

                floor = st.number_input(
                    "Tầng",
                    min_value=1,
                    max_value=100,
                    value=1,
                    step=1,
                )

            note = st.text_area("Ghi chú")

            submitted = st.form_submit_button(
                "➕ Thêm phòng",
                type="primary",
                use_container_width=True,
            )

            if submitted:
                room_number = room_number.strip()

                if not room_number:
                    st.error("Vui lòng nhập số phòng.")

                else:
                    try:
                        execute(
                            """
                            INSERT INTO rooms
                            (
                                room_number,
                                room_type,
                                price,
                                floor,
                                status,
                                note
                            )
                            VALUES (?, ?, ?, ?, 'Trống', ?)
                            """,
                            (
                                room_number,
                                room_type,
                                price,
                                floor,
                                note,
                            ),
                        )

                        st.success(
                            f"Đã thêm phòng {room_number}."
                        )

                    except sqlite3.IntegrityError:
                        st.error(
                            "Số phòng đã tồn tại."
                        )


# ============================================================
# QUẢN LÝ KHÁCH HÀNG
# ============================================================

def customer_management():
    st.header("👤 Quản lý khách hàng")

    tab1, tab2 = st.tabs(
        ["Danh sách khách hàng", "Thêm khách hàng"]
    )

    with tab1:
        customers = get_customers()

        if customers:
            data = [
                {
                    "ID": c["id"],
                    "Họ tên": c["full_name"],
                    "Điện thoại": c["phone"],
                    "Email": c["email"],
                    "CCCD/Passport": c["id_number"],
                    "Địa chỉ": c["address"],
                    "Ngày tạo": format_date(
                        c["created_at"][:10]
                    ),
                }
                for c in customers
            ]

            df = pd.DataFrame(data)

            search = st.text_input(
                "🔎 Tìm khách hàng",
                placeholder="Tên, số điện thoại, CCCD...",
            )

            if search:
                search_lower = search.lower()

                mask = (
                    df["Họ tên"]
                    .astype(str)
                    .str.lower()
                    .str.contains(search_lower, na=False)
                    |
                    df["Điện thoại"]
                    .astype(str)
                    .str.lower()
                    .str.contains(search_lower, na=False)
                    |
                    df["CCCD/Passport"]
                    .astype(str)
                    .str.lower()
                    .str.contains(search_lower, na=False)
                )

                df = df[mask]

            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
            )

        else:
            st.info("Chưa có khách hàng.")

    with tab2:
        with st.form("add_customer_form"):
            full_name = st.text_input(
                "Họ và tên *"
            )

            c1, c2 = st.columns(2)

            with c1:
                phone = st.text_input(
                    "Số điện thoại"
                )

                id_number = st.text_input(
                    "CCCD / Passport"
                )

            with c2:
                email = st.text_input(
                    "Email"
                )

                address = st.text_input(
                    "Địa chỉ"
                )

            submitted = st.form_submit_button(
                "➕ Thêm khách hàng",
                type="primary",
                use_container_width=True,
            )

            if submitted:
                if not full_name.strip():
                    st.error(
                        "Vui lòng nhập họ tên khách hàng."
                    )
                else:
                    execute(
                        """
                        INSERT INTO customers
                        (
                            full_name,
                            phone,
                            email,
                            id_number,
                            address,
                            created_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            full_name.strip(),
                            phone.strip(),
                            email.strip(),
                            id_number.strip(),
                            address.strip(),
                            datetime.now().isoformat(
                                timespec="seconds"
                            ),
                        ),
                    )

                    st.success(
                        "Đã thêm khách hàng."
                    )


# ============================================================
# ĐẶT PHÒNG
# ============================================================

def booking_management():
    st.header("📅 Đặt phòng")

    customers = get_customers()
    rooms = get_rooms("Trống")

    if not customers:
        st.warning(
            "Chưa có khách hàng. Hãy thêm khách hàng trước."
        )
        return

    if not rooms:
        st.warning(
            "Hiện không có phòng trống."
        )
        return

    customer_options = {
        f"{c['full_name']} - {c['phone'] or 'Không có SĐT'}": c["id"]
        for c in customers
    }

    room_options = {
        f"Phòng {r['room_number']} - "
        f"{r['room_type']} - {money(r['price'])}/đêm": r["id"]
        for r in rooms
    }

    with st.form("booking_form"):
        st.subheader("Thông tin đặt phòng")

        customer_label = st.selectbox(
            "Khách hàng *",
            list(customer_options.keys()),
        )

        room_label = st.selectbox(
            "Phòng *",
            list(room_options.keys()),
        )

        c1, c2 = st.columns(2)

        with c1:
            check_in = st.date_input(
                "Ngày nhận phòng *",
                value=date.today(),
            )

        with c2:
            check_out = st.date_input(
                "Ngày trả phòng *",
                value=date.today(),
            )

        c1, c2 = st.columns(2)

        with c1:
            adults = st.number_input(
                "Số người lớn",
                min_value=1,
                value=1,
                step=1,
            )

        with c2:
            children = st.number_input(
                "Số trẻ em",
                min_value=0,
                value=0,
                step=1,
            )

        extra_charge = st.number_input(
            "Phụ thu",
            min_value=0.0,
            value=0.0,
            step=50000.0,
        )

        discount = st.number_input(
            "Giảm giá",
            min_value=0.0,
            value=0.0,
            step=50000.0,
        )

        deposit = st.number_input(
            "Tiền đặt cọc",
            min_value=0.0,
            value=0.0,
            step=50000.0,
        )

        note = st.text_area(
            "Ghi chú"
        )

        submitted = st.form_submit_button(
            "📝 Tạo đặt phòng",
            type="primary",
            use_container_width=True,
        )

        if submitted:
            if check_out <= check_in:
                st.error(
                    "Ngày trả phòng phải sau ngày nhận phòng."
                )
                return

            room_id = room_options[room_label]

            room = next(
                r for r in rooms if r["id"] == room_id
            )

            customer_id = customer_options[
                customer_label
            ]

            days, total = calculate_total(
                float(room["price"]),
                check_in,
                check_out,
                extra_charge,
                discount,
            )

            booking_code = generate_booking_code()

            execute(
                """
                INSERT INTO bookings
                (
                    booking_code,
                    customer_id,
                    room_id,
                    check_in,
                    check_out,
                    adults,
                    children,
                    room_price,
                    extra_charge,
                    discount,
                    total_amount,
                    deposit,
                    status,
                    payment_status,
                    note,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    booking_code,
                    customer_id,
                    room_id,
                    check_in.isoformat(),
                    check_out.isoformat(),
                    adults,
                    children,
                    room["price"],
                    extra_charge,
                    discount,
                    total,
                    deposit,
                    "Đã đặt",
                    "Đã cọc" if deposit > 0 else "Chưa thanh toán",
                    note,
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),
                ),
            )

            st.success(
                f"Đã tạo đặt phòng {booking_code}. "
                f"Tổng tiền: {money(total)} "
                f"({days} đêm)."
            )

    st.divider()

    st.subheader("Danh sách đặt phòng")

    bookings = get_bookings()

    if bookings:
        data = [
            {
                "Mã đặt phòng": b["booking_code"],
                "Khách hàng": b["customer_name"],
                "Phòng": b["room_number"],
                "Nhận phòng": format_date(b["check_in"]),
                "Trả phòng": format_date(b["check_out"]),
                "Tổng tiền": money(b["total_amount"]),
                "Đặt cọc": money(b["deposit"]),
                "Trạng thái": b["status"],
                "Thanh toán": b["payment_status"],
            }
            for b in bookings
        ]

        st.dataframe(
            pd.DataFrame(data),
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# CHECK-IN / CHECK-OUT
# ============================================================

def checkin_checkout():
    st.header("🔑 Nhận phòng / Trả phòng")

    bookings = get_bookings()

    if not bookings:
        st.info("Chưa có đặt phòng.")
        return

    booking_options = {
        f"{b['booking_code']} | "
        f"Phòng {b['room_number']} | "
        f"{b['customer_name']} | "
        f"{b['status']}": b["id"]
        for b in bookings
        if b["status"] not in ("Đã trả phòng", "Đã hủy")
    }

    if not booking_options:
        st.info(
            "Không có đặt phòng cần xử lý."
        )
        return

    selected_label = st.selectbox(
        "Chọn đặt phòng",
        list(booking_options.keys()),
    )

    booking_id = booking_options[selected_label]
    booking = get_booking_by_id(booking_id)

    if not booking:
        st.error("Không tìm thấy đặt phòng.")
        return

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Khách hàng",
        booking["customer_name"],
    )

    c2.metric(
        "Phòng",
        booking["room_number"],
    )

    c3.metric(
        "Tổng tiền",
        money(booking["total_amount"]),
    )

    st.write(
        f"**Nhận:** {format_date(booking['check_in'])}  \n"
        f"**Trả:** {format_date(booking['check_out'])}  \n"
        f"**Số người:** {booking['adults']} người lớn, "
        f"{booking['children']} trẻ em"
    )

    st.divider()

    if booking["status"] == "Đã đặt":
        st.subheader("Nhận phòng")

        if st.button(
            "🔑 Xác nhận nhận phòng",
            type="primary",
            use_container_width=True,
        ):
            execute(
                """
                UPDATE bookings
                SET status = 'Đã nhận phòng'
                WHERE id = ?
                """,
                (booking_id,),
            )

            execute(
                """
                UPDATE rooms
                SET status = 'Đang ở'
                WHERE id = ?
                """,
                (booking["room_id"],),
            )

            st.success(
                "Đã nhận phòng thành công."
            )
            st.rerun()

    elif booking["status"] == "Đã nhận phòng":
        st.subheader("Trả phòng")

        payment_methods = [
            "Tiền mặt",
            "Chuyển khoản",
            "Thẻ",
            "Ví điện tử",
        ]

        payment_method = st.selectbox(
            "Phương thức thanh toán",
            payment_methods,
        )

        paid_before = execute(
            """
            SELECT COALESCE(SUM(amount), 0)
            FROM payments
            WHERE booking_id = ?
            """,
            (booking_id,),
            fetch=True,
        )[0][0]

        deposit = float(booking["deposit"] or 0)
        total = float(booking["total_amount"] or 0)

        already_paid = float(paid_before or 0)
        remaining = max(
            total - deposit - already_paid,
            0,
        )

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Tổng tiền",
            money(total),
        )

        c2.metric(
            "Đã thanh toán",
            money(deposit + already_paid),
        )

        c3.metric(
            "Còn phải thu",
            money(remaining),
        )

        payment_amount = st.number_input(
            "Số tiền thanh toán",
            min_value=0.0,
            value=remaining,
            step=50000.0,
        )

        if st.button(
            "💳 Thanh toán & trả phòng",
            type="primary",
            use_container_width=True,
        ):
            if payment_amount > 0:
                execute(
                    """
                    INSERT INTO payments
                    (
                        booking_id,
                        amount,
                        payment_method,
                        payment_date,
                        note
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        booking_id,
                        payment_amount,
                        payment_method,
                        datetime.now().isoformat(
                            timespec="seconds"
                        ),
                        "Thanh toán khi trả phòng",
                    ),
                )

            execute(
                """
                UPDATE bookings
                SET
                    status = 'Đã trả phòng',
                    payment_status = 'Đã thanh toán'
                WHERE id = ?
                """,
                (booking_id,),
            )

            execute(
                """
                UPDATE rooms
                SET status = 'Trống'
                WHERE id = ?
                """,
                (booking["room_id"],),
            )

            st.success(
                "Đã trả phòng và cập nhật thanh toán."
            )
            st.rerun()

    elif booking["status"] == "Đã trả phòng":
        st.success(
            "Đặt phòng này đã hoàn tất."
        )


# ============================================================
# THANH TOÁN
# ============================================================

def payment_management():
    st.header("💳 Thanh toán")

    bookings = get_bookings()

    if not bookings:
        st.info("Chưa có dữ liệu đặt phòng.")
        return

    rows = []

    for booking in bookings:
        paid = execute(
            """
            SELECT COALESCE(SUM(amount), 0)
            FROM payments
            WHERE booking_id = ?
            """,
            (booking["id"],),
            fetch=True,
        )[0][0]

        total = float(booking["total_amount"] or 0)
        deposit = float(booking["deposit"] or 0)

        rows.append(
            {
                "Mã": booking["booking_code"],
                "Khách hàng": booking["customer_name"],
                "Phòng": booking["room_number"],
                "Tổng tiền": total,
                "Đặt cọc": deposit,
                "Đã thanh toán thêm": float(paid or 0),
                "Còn lại": max(
                    total - deposit - float(paid or 0),
                    0,
                ),
                "Trạng thái": booking["payment_status"],
            }
        )

    df = pd.DataFrame(rows)

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Tổng tiền": st.column_config.NumberColumn(
                format="%,.0f ₫"
            ),
            "Đặt cọc": st.column_config.NumberColumn(
                format="%,.0f ₫"
            ),
            "Đã thanh toán thêm": st.column_config.NumberColumn(
                format="%,.0f ₫"
            ),
            "Còn lại": st.column_config.NumberColumn(
                format="%,.0f ₫"
            ),
        },
    )

    st.divider()

    st.subheader("Lịch sử giao dịch")

    payments = execute(
        """
        SELECT
            p.*,
            b.booking_code,
            c.full_name AS customer_name,
            r.room_number
        FROM payments p
        JOIN bookings b ON p.booking_id = b.id
        JOIN customers c ON b.customer_id = c.id
        JOIN rooms r ON b.room_id = r.id
        ORDER BY p.id DESC
        """,
        fetch=True,
    )

    if payments:
        payment_data = [
            {
                "Mã đặt phòng": p["booking_code"],
                "Khách hàng": p["customer_name"],
                "Phòng": p["room_number"],
                "Số tiền": money(p["amount"]),
                "Phương thức": p["payment_method"],
                "Ngày": format_date(
                    p["payment_date"][:10]
                ),
                "Ghi chú": p["note"],
            }
            for p in payments
        ]

        st.dataframe(
            pd.DataFrame(payment_data),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Chưa có giao dịch.")


# ============================================================
# BÁO CÁO
# ============================================================

def reports():
    st.header("📊 Báo cáo & doanh thu")

    bookings = get_bookings()

    if not bookings:
        st.info(
            "Chưa có dữ liệu để lập báo cáo."
        )
        return

    df = pd.DataFrame(
        [
            {
                "Mã đặt phòng": b["booking_code"],
                "Khách hàng": b["customer_name"],
                "Phòng": b["room_number"],
                "Loại phòng": b["room_type"],
                "Ngày nhận": b["check_in"],
                "Ngày trả": b["check_out"],
                "Doanh thu": float(
                    b["total_amount"] or 0
                ),
                "Trạng thái": b["status"],
            }
            for b in bookings
        ]
    )

    min_date = min(
        pd.to_datetime(df["Ngày nhận"]).dt.date
    )

    max_date = max(
        pd.to_datetime(df["Ngày trả"]).dt.date
    )

    c1, c2 = st.columns(2)

    with c1:
        from_date = st.date_input(
            "Từ ngày",
            value=min_date,
        )

    with c2:
        to_date = st.date_input(
            "Đến ngày",
            value=max_date,
        )

    if from_date > to_date:
        st.error(
            "Khoảng ngày không hợp lệ."
        )
        return

    df["Ngày nhận_dt"] = pd.to_datetime(
        df["Ngày nhận"]
    ).dt.date

    filtered = df[
        (df["Ngày nhận_dt"] >= from_date)
        &
        (df["Ngày nhận_dt"] <= to_date)
    ].copy()

    total_revenue = filtered["Doanh thu"].sum()

    number_of_bookings = len(filtered)

    completed = len(
        filtered[
            filtered["Trạng thái"]
            == "Đã trả phòng"
        ]
    )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Tổng doanh thu",
        money(total_revenue),
    )

    c2.metric(
        "Số lượt đặt phòng",
        number_of_bookings,
    )

    c3.metric(
        "Đã hoàn tất",
        completed,
    )

    st.divider()

    if not filtered.empty:
        chart_data = (
            filtered
            .groupby("Ngày nhận_dt")["Doanh thu"]
            .sum()
            .reset_index()
        )

        chart_data = chart_data.rename(
            columns={
                "Ngày nhận_dt": "Ngày"
            }
        )

        chart_data = chart_data.set_index("Ngày")

        st.subheader("📈 Doanh thu theo ngày")

        st.bar_chart(
            chart_data["Doanh thu"]
        )

        st.subheader("📋 Chi tiết")

        display_df = filtered[
            [
                "Mã đặt phòng",
                "Khách hàng",
                "Phòng",
                "Loại phòng",
                "Ngày nhận",
                "Ngày trả",
                "Doanh thu",
                "Trạng thái",
            ]
        ]

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Doanh thu": st.column_config.NumberColumn(
                    format="%,.0f ₫"
                )
            },
        )

        csv = display_df.to_csv(
            index=False
        ).encode("utf-8-sig")

        st.download_button(
            "⬇️ Tải báo cáo CSV",
            data=csv,
            file_name="bao_cao_khach_san.csv",
            mime="text/csv",
        )

    else:
        st.info(
            "Không có dữ liệu trong khoảng thời gian này."
        )


# ============================================================
# QUẢN LÝ ĐẶT PHÒNG
# ============================================================

def booking_list():
    st.header("📋 Danh sách đặt phòng")

    bookings = get_bookings()

    if not bookings:
        st.info(
            "Chưa có đặt phòng."
        )
        return

    data = []

    for b in bookings:
        data.append(
            {
                "ID": b["id"],
                "Mã": b["booking_code"],
                "Khách": b["customer_name"],
                "SĐT": b["customer_phone"],
                "Phòng": b["room_number"],
                "Loại": b["room_type"],
                "Check-in": format_date(b["check_in"]),
                "Check-out": format_date(b["check_out"]),
                "Tổng tiền": money(b["total_amount"]),
                "Trạng thái": b["status"],
                "Thanh toán": b["payment_status"],
            }
        )

    df = pd.DataFrame(data)

    c1, c2 = st.columns(2)

    with c1:
        status_filter = st.selectbox(
            "Lọc trạng thái",
            [
                "Tất cả",
                "Đã đặt",
                "Đã nhận phòng",
                "Đã trả phòng",
                "Đã hủy",
            ],
        )

    with c2:
        search = st.text_input(
            "Tìm kiếm",
            placeholder="Mã đặt phòng, tên khách, số phòng...",
        )

    if status_filter != "Tất cả":
        df = df[
            df["Trạng thái"]
            == status_filter
        ]

    if search:
        search = search.lower()

        mask = (
            df["Mã"]
            .astype(str)
            .str.lower()
            .str.contains(search, na=False)
            |
            df["Khách"]
            .astype(str)
            .str.lower()
            .str.contains(search, na=False)
            |
            df["Phòng"]
            .astype(str)
            .str.lower()
            .str.contains(search, na=False)
        )

        df = df[mask]

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        f"Tổng số bản ghi: {len(df)}"
    )


# ============================================================
# SIDEBAR
# ============================================================

def sidebar():
    st.sidebar.markdown(
        '<div class="sidebar-title">🏨 QUẢN LÝ KHÁCH SẠN</div>',
        unsafe_allow_html=True,
    )

    st.sidebar.markdown(
        '<div class="small-text">Hotel Management System</div>',
        unsafe_allow_html=True,
    )

    st.sidebar.divider()

    menu = st.sidebar.radio(
        "MENU",
        [
            "📊 Dashboard",
            "🛏️ Quản lý phòng",
            "👤 Khách hàng",
            "📅 Đặt phòng",
            "📋 Danh sách đặt phòng",
            "🔑 Nhận / Trả phòng",
            "💳 Thanh toán",
            "📈 Báo cáo",
        ],
    )

    st.sidebar.divider()

    st.sidebar.info(
        "💡 Dữ liệu được lưu tự động "
        "trong cơ sở dữ liệu SQLite."
    )

    return menu


# ============================================================
# MAIN
# ============================================================

def main():
    init_database()

    menu = sidebar()

    if menu == "📊 Dashboard":
        dashboard()

    elif menu == "🛏️ Quản lý phòng":
        room_management()

    elif menu == "👤 Khách hàng":
        customer_management()

    elif menu == "📅 Đặt phòng":
        booking_management()

    elif menu == "📋 Danh sách đặt phòng":
        booking_list()

    elif menu == "🔑 Nhận / Trả phòng":
        checkin_checkout()

    elif menu == "💳 Thanh toán":
        payment_management()

    elif menu == "📈 Báo cáo":
        reports()


if __name__ == "__main__":
    main()
