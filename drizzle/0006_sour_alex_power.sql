CREATE TABLE `productTrendTags` (
	`id` int AUTO_INCREMENT NOT NULL,
	`productId` int NOT NULL,
	`tag` varchar(120) NOT NULL,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `productTrendTags_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
ALTER TABLE `products` ADD `isTrending` boolean DEFAULT false NOT NULL;