CREATE TABLE `customerRewards` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int NOT NULL,
	`rewardType` enum('gift','coupon','order_threshold','quantity_threshold') NOT NULL,
	`title` varchar(180) NOT NULL,
	`couponCode` varchar(80),
	`discountType` enum('fixed','percent') NOT NULL DEFAULT 'fixed',
	`discountValue` int NOT NULL DEFAULT 0,
	`minimumOrderAmount` int NOT NULL DEFAULT 0,
	`minimumQuantity` int NOT NULL DEFAULT 0,
	`giftName` varchar(180),
	`isActive` boolean NOT NULL DEFAULT true,
	`assignedByUserId` int NOT NULL,
	`expiresAt` timestamp,
	`usedAt` timestamp,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `customerRewards_id` PRIMARY KEY(`id`),
	CONSTRAINT `customerRewards_couponCode_unique` UNIQUE(`couponCode`)
);
