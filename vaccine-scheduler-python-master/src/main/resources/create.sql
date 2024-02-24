CREATE TABLE Caregivers (
    Username varchar(255),
    Salt BINARY(16),
    Hash BINARY(16),
    PRIMARY KEY (Username)
);

CREATE TABLE Availabilities (
    Time date,
    Username varchar(255) REFERENCES Caregivers,
    PRIMARY KEY (Time, Username)
);

CREATE TABLE Vaccines (
    Name varchar(255),
    Doses int,
    PRIMARY KEY (Name)
);

CREATE TABLE Patients (
    Username varchar(255),
    Salt BINARY(16),
    Hash BINARY(16),
    PRIMARY KEY (Username)
);

CREATE TABLE Appointments (
    app_id INT,
    p_username VARCHAR(255),
    c_username VARCHAR(255),
    v_name VARCHAR(255) DEFAULT NULL,
    Time date,
    FOREIGN KEY (p_username) REFERENCES Patients(Username),
    FOREIGN KEY (c_username) REFERENCES Caregivers(Username),
    FOREIGN KEY (v_name) REFERENCES Vaccines(Name),
    PRIMARY KEY (app_id)
);
