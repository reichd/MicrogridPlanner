DROP TABLE IF EXISTS `resilience_user` ;
DROP TABLE IF EXISTS `resilience` ;
DROP TABLE IF EXISTS `repair_user` ;
DROP TABLE IF EXISTS `repair_data` ;
DROP TABLE IF EXISTS `repair` ;
DROP TABLE IF EXISTS `disturbance_user` ;
DROP TABLE IF EXISTS `disturbance_data` ;
DROP TABLE IF EXISTS `disturbance` ;

-- Table `disturbance`
CREATE TABLE IF NOT EXISTS `disturbance` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(32) NOT NULL,
  `description` VARCHAR(128) NULL DEFAULT NULL,
  `gridId` INT NOT NULL,
  PRIMARY KEY (`id`),
  CONSTRAINT `fk_disturbance_grid`
    FOREIGN KEY (`gridId`)
    REFERENCES `grid` (`id`)
    ON DELETE CASCADE
);


-- Table `disturbance_data`
CREATE TABLE IF NOT EXISTS `disturbance_data` (
  `disturbanceId` INT NOT NULL,
  `componentId` INT NOT NULL,
  `quantity` INT NOT NULL,
  `value` FLOAT DEFAULT 1.0,
  PRIMARY KEY (`disturbanceId`, `componentId`),  
  INDEX `fk_disturbance_idx` (`disturbanceId`),  
  CONSTRAINT `fk_disturbance`
    FOREIGN KEY (`disturbanceId`)
    REFERENCES `disturbance` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_disturbance_component`
    FOREIGN KEY (`componentId`)
    REFERENCES `component` (`id`)
    ON DELETE CASCADE
);


-- Table `disturbance_user`
CREATE TABLE IF NOT EXISTS `disturbance_user` (
  `disturbanceId` INT NOT NULL,
  `userId` INT NOT NULL,
  `permissionId` INT NOT NULL,
  PRIMARY KEY (`disturbanceId`, `userId`),
  INDEX `fk_disturbanceuser_user_idx` (`userId` ASC),
  INDEX `fk_disturbance_user_permission_idx` (`permissionId` ASC),
  CONSTRAINT `fk_disturbance_user_permission`
    FOREIGN KEY (`permissionId`)
    REFERENCES `permission` (`id`),
  CONSTRAINT `fk_disturbanceuser_disturbance`
    FOREIGN KEY (`disturbanceId`)
    REFERENCES `disturbance` (`id`)
    ON DELETE CASCADE
);


-- Table `repair`
CREATE TABLE IF NOT EXISTS `repair` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(32) NOT NULL,
  `description` VARCHAR(128) NULL DEFAULT NULL,
  `gridId` INT NOT NULL,
  PRIMARY KEY (`id`),
  CONSTRAINT `fk_repair_grid`
    FOREIGN KEY (`gridId`)
    REFERENCES `grid` (`id`)
    ON DELETE CASCADE
);


-- Table `repair_data`
CREATE TABLE IF NOT EXISTS `repair_data` (
  `repairId` INT NOT NULL,
  `componentId` INT NOT NULL,
  `value` FLOAT NOT NULL,
  PRIMARY KEY (`repairId`, `componentId`),  
  INDEX `fk_repair_idx` (`repairId` ASC),  
  CONSTRAINT `fk_repair`
    FOREIGN KEY (`repairId`)
    REFERENCES `repair` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_repair_component`
    FOREIGN KEY (`componentId`)
    REFERENCES `component` (`id`)
    ON DELETE CASCADE
);


-- Table `repair_user`
CREATE TABLE IF NOT EXISTS `repair_user` (
  `repairId` INT NOT NULL,
  `userId` INT NOT NULL,
  `permissionId` INT NOT NULL,
  PRIMARY KEY (`repairId`, `userId`),
  INDEX `fk_repairuser_user_idx` (`userId` ASC),
  INDEX `fk_repair_user_permission_idx` (`permissionId` ASC),
  CONSTRAINT `fk_repair_user_permission`
    FOREIGN KEY (`permissionId`)
    REFERENCES `permission` (`id`),
  CONSTRAINT `fk_repairuser_repair`
    FOREIGN KEY (`repairId`)
    REFERENCES `repair` (`id`)
    ON DELETE CASCADE
);

-- Table `resilience`
CREATE TABLE IF NOT EXISTS `resilience` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `gridId` INT NOT NULL,
  `energyManagementSystemId` INT NOT NULL,
  `powerloadId` INT NOT NULL,
  `locationId` INT NOT NULL,
  `startdatetime` DATETIME NOT NULL,
  `enddatetime` DATETIME NOT NULL,
  `disturbanceId` INT NOT NULL,  
  `disturbanceStartdatetime` DATETIME NOT NULL,
  `repairId` INT NOT NULL,
  `extendTimeframe` FLOAT NOT NULL,
  `numRuns` INT NOT NULL,
  `numShiftHours` INT NOT NULL,
  `method` VARCHAR(16) NOT NULL,
  `results` MEDIUMBLOB DEFAULT NULL,
  `computeJobId` VARCHAR(16) DEFAULT NULL,
  `runsubmitdatetime` DATETIME DEFAULT NULL,
  `runstartdatetime` DATETIME DEFAULT NULL,
  `runenddatetime` DATETIME DEFAULT NULL,
  `success` BOOLEAN DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `resilience_unique` (`gridId`,`energyManagementSystemId`,`powerloadId`,`locationId`,
                                  `startdatetime`,`enddatetime`,`disturbanceId`,`disturbanceStartdatetime`,
                                  `repairId`,`extendTimeframe`,`numShiftHours`,`numRuns`,`method`),
  CONSTRAINT `fk_resilience_grid` 
    FOREIGN KEY (`gridId`)
    REFERENCES `grid` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_resilience_energy_management_system` 
    FOREIGN KEY (`energyManagementSystemId`)
    REFERENCES `energy_management_system` (`id`),
  CONSTRAINT `fk_resilience_powerload`
    FOREIGN KEY (`powerloadId`)
    REFERENCES `powerload` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_resilience_disturbance`
    FOREIGN KEY (`disturbanceId`)
    REFERENCES `disturbance` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_resilience_repair`
    FOREIGN KEY (`repairId`)
    REFERENCES `repair` (`id`)
    ON DELETE CASCADE
);

-- Table `resilience_user`
CREATE TABLE IF NOT EXISTS `resilience_user` (
  `resilienceId` INT NOT NULL,
  `userId` INT NOT NULL,
  `permissionId` INT NOT NULL,
  PRIMARY KEY (`resilienceId`, `userId`),
  INDEX `fk_resilience_user_idx` (`userId` ASC),
  INDEX `fk_resilience_user_permission_idx` (`permissionId` ASC),
  CONSTRAINT `fk_resilience_user_permission`
    FOREIGN KEY (`permissionId`)
    REFERENCES `permission` (`id`),
  CONSTRAINT `fk_resilience_user_id`
    FOREIGN KEY (`resilienceId`)
    REFERENCES `resilience` (`id`)
    ON DELETE CASCADE
);
