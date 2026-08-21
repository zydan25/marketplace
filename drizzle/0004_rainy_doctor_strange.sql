CREATE TABLE `storefrontCircleSections` (
	`id` int AUTO_INCREMENT NOT NULL,
	`tabId` int NOT NULL,
	`title` varchar(100) NOT NULL,
	`targetCategory` varchar(120),
	`storageKey` varchar(512),
	`imageUrl` varchar(1024),
	`sortOrder` int NOT NULL DEFAULT 0,
	`isActive` boolean NOT NULL DEFAULT true,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `storefrontCircleSections_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `storefrontSlides` (
	`id` int AUTO_INCREMENT NOT NULL,
	`tabId` int NOT NULL,
	`title` varchar(180),
	`subtitle` varchar(255),
	`ctaLabel` varchar(80),
	`storageKey` varchar(512) NOT NULL,
	`imageUrl` varchar(1024) NOT NULL,
	`sortOrder` int NOT NULL DEFAULT 0,
	`isActive` boolean NOT NULL DEFAULT true,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `storefrontSlides_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `storefrontTabs` (
	`id` int AUTO_INCREMENT NOT NULL,
	`title` varchar(90) NOT NULL,
	`searchPlaceholder` varchar(180),
	`sortOrder` int NOT NULL DEFAULT 0,
	`isActive` boolean NOT NULL DEFAULT true,
	`createdByUserId` int NOT NULL,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `storefrontTabs_id` PRIMARY KEY(`id`)
);
