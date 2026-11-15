ALTER TABLE `workspace_commits` ADD `kernel_source_hash` text NOT NULL;--> statement-breakpoint
ALTER TABLE `workspace_commits` ADD `context` text NOT NULL;--> statement-breakpoint
ALTER TABLE `workspaces` ADD `genesis` text NOT NULL;