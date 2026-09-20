CREATE INDEX ix_devices_device_type ON devices (device_type)

CREATE INDEX ix_devices_is_available ON devices (is_available)

CREATE INDEX ix_loans_device_id ON loans (device_id)

CREATE INDEX ix_loans_status ON loans (status)

CREATE INDEX ix_loans_user_id ON loans (user_id)

CREATE UNIQUE INDEX ix_users_email ON users (email)

CREATE INDEX ix_users_id ON users (id)

CREATE INDEX ix_users_is_active ON users (is_active)

CREATE INDEX ix_users_role ON users (role)

CREATE UNIQUE INDEX uq_loans_open_device ON loans (device_id) WHERE status IN ('active', 'overdue')

CREATE TABLE alembic_version (
	version_num VARCHAR(32) NOT NULL,
	CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
)

CREATE TABLE devices (
	id INTEGER NOT NULL,
	name VARCHAR(120) NOT NULL,
	serial_number VARCHAR(100) NOT NULL,
	device_type VARCHAR(50) NOT NULL,
	brand VARCHAR(80),
	is_available BOOLEAN DEFAULT '1' NOT NULL,
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_devices_type CHECK (length(trim(device_type)) > 0),
	CONSTRAINT ck_devices_name CHECK (length(trim(name)) > 0),
	CONSTRAINT ck_devices_serial CHECK (length(trim(serial_number)) > 0),
	UNIQUE (serial_number)
)

CREATE TABLE loans (
	id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	device_id INTEGER NOT NULL,
	loan_date DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL,
	return_date DATETIME,
	status VARCHAR(20) DEFAULT 'active' NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_loans_return_status CHECK ((status = 'returned' AND return_date IS NOT NULL) OR (status != 'returned' AND return_date IS NULL)),
	CONSTRAINT ck_loans_status CHECK (status IN ('active', 'returned', 'overdue')),
	CONSTRAINT ck_loans_dates CHECK (return_date IS NULL OR return_date >= loan_date),
	FOREIGN KEY(device_id) REFERENCES devices (id) ON DELETE RESTRICT,
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE RESTRICT
)

CREATE TABLE users (
	id INTEGER NOT NULL,
	name VARCHAR(80) NOT NULL,
	email VARCHAR(254) NOT NULL,
	role VARCHAR(20) NOT NULL,
	is_active BOOLEAN NOT NULL,
	internal_notes VARCHAR(255) NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_users_role_allowed CHECK (role IN ('admin', 'support', 'user')),
	CONSTRAINT ck_users_email_max_length CHECK (length(email) <= 254),
	CONSTRAINT ck_users_name_max_length CHECK (length(name) <= 80),
	CONSTRAINT ck_users_name_min_length CHECK (length(trim(name)) >= 3)
)
