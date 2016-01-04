/*
SQLyog Ultimate v9.01 
MySQL - 5.6.27-0ubuntu0.14.04.1 
*********************************************************************
*/
/*!40101 SET NAMES utf8 */;

create table `address_book` (
	`id` int (11),
	`phone` varchar (54),
	`home` varchar (300),
	`office` varchar (300)
); 
insert into `address_book` (`id`, `phone`, `home`, `office`) values('1','13800138000','changde','shenzhen');
insert into `address_book` (`id`, `phone`, `home`, `office`) values('3','111','abc','dde');
insert into `address_book` (`id`, `phone`, `home`, `office`) values('5','asdf','aa','sadfad');
