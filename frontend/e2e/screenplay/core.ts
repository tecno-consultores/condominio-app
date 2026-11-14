// SPDX-License-Identifier: MIT
// Copyright (C) 2026 Condominio App Contributors

import type { Page } from '@playwright/test';

export interface Ability {
  readonly name: string;
}

export class BrowseTheWeb implements Ability {
  readonly name = 'BrowseTheWeb';

  private constructor(public readonly page: Page) {}

  static using(page: Page): BrowseTheWeb {
    return new BrowseTheWeb(page);
  }
}

export interface Task {
  readonly description: string;
  performAs(actor: Actor): Promise<void>;
}

export interface Question<T> {
  readonly description: string;
  answeredBy(actor: Actor): Promise<T>;
}

export class Actor {
  private readonly abilities = new Map<string, Ability>();

  private constructor(public readonly name: string) {}

  static named(name: string): Actor {
    return new Actor(name);
  }

  whoCan(...abilities: Ability[]): this {
    for (const ability of abilities) {
      this.abilities.set(ability.name, ability);
    }
    return this;
  }

  abilityTo<T extends Ability>(abilityName: string): T {
    const ability = this.abilities.get(abilityName);
    if (!ability) {
      throw new Error(`El actor "${this.name}" no posee la habilidad "${abilityName}".`);
    }
    return ability as T;
  }

  page(): Page {
    return this.abilityTo<BrowseTheWeb>('BrowseTheWeb').page;
  }

  async attemptsTo(...tasks: Task[]): Promise<void> {
    for (const task of tasks) {
      await task.performAs(this);
    }
  }

  async asks<T>(question: Question<T>): Promise<T> {
    return question.answeredBy(this);
  }
}

export async function waitForDialogSettled(page: Page, selector: string): Promise<void> {
  const locator = page.locator(selector);
  await locator.waitFor({ state: 'visible' });
  await page.evaluate(async (sel) => {
    const el = document.querySelector(sel);
    if (el && typeof el.getAnimations === 'function') {
      await Promise.allSettled(el.getAnimations().map((anim) => anim.finished));
    }
    await document.fonts.ready;
  }, selector);
}
