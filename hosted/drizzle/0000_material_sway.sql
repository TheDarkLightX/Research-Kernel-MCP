CREATE TABLE `workspace_commits` (
	`id` text PRIMARY KEY NOT NULL,
	`workspace_id` text NOT NULL,
	`revision` integer NOT NULL,
	`actor` text NOT NULL,
	`command` text NOT NULL,
	`state_hash` text NOT NULL,
	`previous_hash` text NOT NULL,
	`checker_source_hash` text NOT NULL,
	`at` text NOT NULL,
	FOREIGN KEY (`workspace_id`) REFERENCES `workspaces`(`id`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE UNIQUE INDEX `workspace_revision_idx` ON `workspace_commits` (`workspace_id`,`revision`);--> statement-breakpoint
CREATE TABLE `workspaces` (
	`id` text PRIMARY KEY NOT NULL,
	`name` text NOT NULL,
	`owner` text NOT NULL,
	`revision` integer NOT NULL,
	`state` text NOT NULL,
	`last_commit` text NOT NULL,
	`updated_at` text NOT NULL
);
--> statement-breakpoint
CREATE INDEX `workspace_owner_idx` ON `workspaces` (`owner`);