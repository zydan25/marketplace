CREATE TABLE `productCategoryAssignments` (
	`id` int AUTO_INCREMENT NOT NULL,
	`productId` int NOT NULL,
	`category` varchar(120) NOT NULL,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `productCategoryAssignments_id` PRIMARY KEY(`id`)
);
