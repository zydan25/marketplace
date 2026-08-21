CREATE TABLE `marketingNotificationRecipients` (
	`id` int AUTO_INCREMENT NOT NULL,
	`notificationId` int NOT NULL,
	`userId` int NOT NULL,
	`isRead` boolean NOT NULL DEFAULT false,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `marketingNotificationRecipients_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `marketingNotifications` (
	`id` int AUTO_INCREMENT NOT NULL,
	`title` varchar(180) NOT NULL,
	`body` text NOT NULL,
	`imageStorageKey` varchar(512),
	`imageUrl` varchar(1024),
	`productId` int,
	`audienceType` enum('governorate','single','selected') NOT NULL,
	`governorate` varchar(80),
	`createdByUserId` int NOT NULL,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `marketingNotifications_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `referralSettings` (
	`id` int AUTO_INCREMENT NOT NULL,
	`isEnabled` boolean NOT NULL DEFAULT false,
	`updatedByUserId` int NOT NULL,
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `referralSettings_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `referrals` (
	`id` int AUTO_INCREMENT NOT NULL,
	`inviterUserId` int NOT NULL,
	`invitedUserId` int NOT NULL,
	`referralCode` varchar(80) NOT NULL,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `referrals_id` PRIMARY KEY(`id`),
	CONSTRAINT `referrals_invitedUserId_unique` UNIQUE(`invitedUserId`)
);
--> statement-breakpoint
ALTER TABLE `products` ADD `productCode` varchar(80) NOT NULL;--> statement-breakpoint
ALTER TABLE `products` ADD CONSTRAINT `products_productCode_unique` UNIQUE(`productCode`);