CREATE TABLE `publication_packages` (
	`id` text PRIMARY KEY NOT NULL,
	`workspace_id` text NOT NULL,
	`packet` text NOT NULL,
	`revoked` integer NOT NULL,
	`at` text NOT NULL,
	FOREIGN KEY (`workspace_id`) REFERENCES `workspaces`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE INDEX `publication_catalog_idx` ON `publication_packages` (`revoked`,`at`);