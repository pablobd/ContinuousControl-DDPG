import numpy as np
from collections import namedtuple, deque
import random, copy

from model import Actor, Critic

import torch
import torch.nn.functional as F
import torch.optim as optim

BUFFER_SIZE = int(1e6)  # replay buffer size
BATCH_SIZE = 128        # minibatch size
GAMMA = 0.99            # discount factor
TAU = 1e-3              # for soft update of target parameters
LR_ACTOR = 1e-4         # learning rate of the actor 
LR_CRITIC = 3e-4        # learning rate of the critic
WEIGHT_DECAY = 0.0001   # L2 weight decay

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")


class Agent:
    " Interacts with and learns from the environment "
    
    
    def __init__(self, action_size, state_size, hidden_layers = [256, 64], random_seed = 123):
        """ Initialize attributes of Agent        
        Params
        ======
            state_size (int): dimension of each state
            action_size (int): dimension of each action
            random_seed (int): random seed
        """
        
        self.action_size = action_size
        self.states_size = state_size
        self.seed = random.seed(random_seed)
        
        self.local_actor = Actor(action_size, state_size, random_seed, hidden_layers)
        self.target_actor = Actor(action_size, state_size, random_seed, hidden_layers)
        self.actor_optimizer = optim.Adam(self.actor_local.parameters(), lr=LR_ACTOR)

        self.local_critic = Critic(action_size, state_size, random_seed, hidden_layers)
        self.target_critic = Critic(action_size, state_size, random_seed, hidden_layers)
        self.critic_optimizer = optim.Adam(self.critic_local.parameters(), lr=LR_CRITIC, weight_decay=WEIGHT_DECAY)        
        
        self.experiencies = ReplayBuffer(BUFFER_SIZE, BATCH_SIZE)
        
    def step(self, state, action, reward, next_state, done):
        """ Saves experience in replay memory, and uses random sample from buffer to learn        
        Params
        ======
            state (float ndarray): state of the environment
            action (float ndarray): action chosen by agent
            reward (float ndarray):  reward given by environment after doing this action
            next_state (float ndarray): state of the environment after doing this action
            done (float ndarray): flag indicating if episode has finished after doing this action
        """
        
        self.experiences.add(state, action, reward, next_state, done)
        
        if len(self.experiences) > BATCH_SIZE:
            batch = self.experiences.sample()
            self.learn(batch)
        
        
    def act(self, state, add_noise = True):
        """ Given a state choose an action
        Params
        ======
            state (float ndarray): state of the environment        
        """
        state = torch.from_numpy(state).float().to(device)
        self.local_actor.eval() # set network on eval mode, this has any effect only on certain modules (Dropout, BatchNorm, etc.)
        
        with torch.no_grad():
            action = self.local_actor(state).cpu().data.numpy()
            
        """self.local_actor.train() # set nework on train mode
        if add_noise:
            action += self.noise.sample()
        return np.clip(action, -1, 1)"""
        
        return action
    
    def learn(self, batch, gamma = GAMMA):
        """ given a batch of experiences, perform gradient ascent on the local networks and soft update on target networks
        Q_targets = r + γ * critic_target(next_state, actor_target(next_state))
        where:
            actor_target(state) -> action
            critic_target(state, action) -> Q-value
            
        Params
        ======
            batch (tuple of torch tensors from ndarray): (states, actions, rewards, next_states, dones)
            gamma (float): discount factor
        """
        states, actions, rewards, next_states, dones = batch
        
               
        # compute critic loss
        Q_local = self.local_critic(states, actions)
        Q_target_next = self.target_critic(next_states, self.local_actor(next_states))
        Q_target = rewards + gamma * Q_next * (1 - dones)
        critic_loss = F.mse_loss(Q_local, Q_target)
        # Minimize the loss
        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        self.critic_optimizer.step()
        
        
        # gradient ascent actor
        Q_local_next = self.local_critic(states, self.local_actor(states))
        actor_loss = - Q_local_next.mean()
        # Minimize the loss
        self.actor_optimizer.zero_grad()
        actor_loss.backward()
        self.critic_optimizer.step()
        
        
        # soft update of target networks
        self.soft_update(self.local_critic, self.target_critic, TAU)
        self.soft_update(self.local_actor, self.target_actor, TAU) 
        
    
    def reset(self):
        self.noise.reset()
    
    def soft_update(self, local_model, target_model, tau):
        """Soft update model parameters.
        θ_target = τ*θ_local + (1 - τ)*θ_target

        Params
        ======
            local_model: PyTorch model (weights will be copied from)
            target_model: PyTorch model (weights will be copied to)
            tau (float): interpolation parameter 
        """
        for target_param, local_param in zip(target_model.parameters(), local_model.parameters()):
            target_param.data.copy_(tau*local_param.data + (1.0-tau)*target_param.data)
            
        
    
class ReplayBuffer:
    " Internal memory of the agent "
    
    def __init__(self, buffer_size, batch_size):
        """Initialize a ReplayBuffer object.
        Params
        ======
            buffer_size (int): maximum size of buffer
            batch_size (int): size of each training batch
        """
    
        self.experience = namedtuple('Experience', ['state', 'action', 'reward', 'next_state', 'done']).float().to(device)
        self.memory = deque()
        self.buffer_size = buffer_size
        self.batch_size = batch_size
        
    def add(self, state, action, reward, next_state, done):
        " Add a new experience to memory "
        
        self.experience = (state, action, reward, next_state, done)
        self.memory.append(experience)
        
    def sample(self):
        " Randomly sample a batch of experiences from the memory "
        
        batch = random.sample(self.memory, self.batch_size)
        
        states = torch.from_numpy([exp.state for exp in batch if exp is not None]).float().to(device)
        actions = torch.from_numpy([exp.action for exp in batch if exp is not None]).float().to(device)
        rewards = torch.from_numpy([exp.reward for exp in batch if exp is not None]).float().to(device)
        next_states = torch.from_numpy([exp.next_state for exp in batch if exp is not None]).float().to(device)
        dones = torch.from_numpy([exp.done for exp in batch if exp is not None]).float().to(device)
        
        return (states, actions, rewards, next_states, dones)
    
    def __len__(self):
        " Return the current size of internal memory. Overwrites the inherited function len. "
        
        return len(self.memory)
        
    
    

