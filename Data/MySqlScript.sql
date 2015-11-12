-- MySQL Workbench Forward Engineering

SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='TRADITIONAL,ALLOW_INVALID_DATES';

-- -----------------------------------------------------
-- Schema mydb
-- -----------------------------------------------------
-- -----------------------------------------------------
-- Schema riothackaton
-- -----------------------------------------------------

-- -----------------------------------------------------
-- Schema riothackaton
-- -----------------------------------------------------
CREATE SCHEMA IF NOT EXISTS `riothackaton` DEFAULT CHARACTER SET utf8 ;
USE `riothackaton` ;

-- -----------------------------------------------------
-- Table `riothackaton`.`summoner`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `riothackaton`.`summoner` (
  `id` BIGINT(20) NOT NULL AUTO_INCREMENT COMMENT '',
  `masteryPoints` INT(11) NULL DEFAULT NULL COMMENT '',
  `masteryRank` INT(11) NULL DEFAULT NULL COMMENT '',
  `region` VARCHAR(255) NULL DEFAULT NULL COMMENT '',
  `summonerId` VARCHAR(255) NULL DEFAULT NULL COMMENT '',
  PRIMARY KEY (`id`)  COMMENT '')
ENGINE = InnoDB
AUTO_INCREMENT = 3010
DEFAULT CHARACTER SET = utf8;


SET SQL_MODE=@OLD_SQL_MODE;
SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS;
